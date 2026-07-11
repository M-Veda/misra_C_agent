# Phase 2 — Human-in-the-Loop Review Platform

The review workflow is the heart of the product. The system **never** applies a
fix automatically. Every violation must pass through an explicit engineer
decision before a patch can even be generated, and patches are export-only —
there is no "apply" operation anywhere in the codebase.

```
Violation Detected → Suggested Fix Generated → Engineer Review
   → Accept | Reject | Edit | Skip | False Positive | Suppress
   → Patch Generation (accept/edit only) → Patch Export → External Application
```

## Architecture Updates

### Domain model (`backend/src/misra_platform/domain/`)
- `ReviewAction` enum: `accept`, `reject`, `edit`, `skip`, `false_positive`, `suppress`
- `ViolationStatus` extended with `accepted`, `rejected`, `edited`, `skipped`, `suppressed`
- `ACTION_TO_STATUS`, `ACTIONS_REQUIRING_JUSTIFICATION`, `ACTIONS_GENERATING_PATCHES`,
  `MIN_JUSTIFICATION_LENGTH` (20 chars) centralize the state-machine rules
- Three new **append-only** tables (no `onupdate`, no update/delete code paths anywhere):
  - `violation_reviews` — one row per review action ever taken on a violation
    (violation_id, action, previous_status, new_status, reviewer_id, reviewer_name,
    justification, notes, edited_fix_json, created_at)
  - `audit_entries` — generic immutable audit log for *any* state-changing action
    (violation review, patch generation, reviewer assignment, bulk operation):
    entity_type, entity_id, action, actor_id, actor_name, old_state_json,
    new_state_json, justification, notes, created_at
  - `patches` — generated (never applied) unified-diff/git-patch artifacts, linked
    to the violation and the review that produced them
- `ViolationRecord` gained `assigned_reviewer_id` / `assigned_reviewer_name` for
  bulk reviewer assignment (mutable pointer field, not part of the audit history)

### Services (`backend/src/misra_platform/services/`)
- `SourceFileService` — sandboxed, read-only file access strictly within a
  project's `root_path` (path-traversal safe); powers the left-panel source
  viewer and the patch engine's line-accurate diffs
- `PatchEngine` — generates unified diff + git-patch text with `difflib`. If the
  original source file cannot be read (e.g. running outside the mounted
  project volume) it falls back to a clearly-labeled best-effort textual patch.
  **No filesystem writes. No apply operation exists in this codebase.**
- `ReviewService.submit_review()` — the single append-only entry point for all
  six review actions: validates justification length for `accept` / `suppress`
  / `false_positive`, validates `edited_fix.suggested_code` for `edit`, inserts
  the review row, updates the violation's current-status pointer, inserts an
  audit entry, and (for `accept`/`edit` only) generates and persists a patch
  plus a `patch.generated` audit entry
- `ReviewService.estimate_impact()` — explainable heuristic combining severity,
  MISRA category (mandatory/required/advisory), and detection confidence into
  a low/medium/high impact estimate with a plain-language summary
- `BulkReviewService` — `bulk_skip`, `bulk_assign_reviewer`,
  `bulk_export_approved_patches`. **There is no `bulk_accept` method or
  endpoint anywhere in the codebase** — every acceptance is an individual,
  justified engineer decision

### APIs
- `POST /api/v1/violations/{id}/reviews` — submit a review action
- `GET /api/v1/violations/{id}/reviews` — full append-only review history
- `GET /api/v1/violations/{id}/patches` — generated patches for a violation
- `GET /api/v1/violations/{id}/patches/{patch_id}/export?format=git|unified` —
  download a patch file (marks it `exported`, never applies it)
- `GET /api/v1/violations/{id}/source` — sandboxed source window for the left panel
- `GET /api/v1/violations/{id}/impact` — impact estimate
- `GET /api/v1/violations/{id}` — single violation fetch (new, needed by the review workspace)
- `GET /api/v1/audit-entries?q=&action=&entity_type=&entity_id=&actor_id=` — searchable audit log
- `POST /api/v1/violations/bulk/skip`
- `POST /api/v1/violations/bulk/assign-reviewer`
- `POST /api/v1/violations/bulk/export-patches`

### Frontend (`frontend/src/features/review/`)
- `ReviewWorkspacePage` — the flagship interface, three-column layout:
  - **Left** — `SourceCodePanel`: read-only Monaco editor showing the real
    source file (when accessible) with the offending line range highlighted
    via decorations and a gutter marker
  - **Center** — `ViolationDetailsPanel`: explanation, risk description, rule
    rationale, confidence gauge, rule metadata link
  - **Right** — `FixPanel`: suggested fix + rationale, editable fix textarea
    (only when the `edit` action is selected), impact estimate, embedded
    `DiffViewer`, and patch preview with export buttons
  - **Bottom** — `ReviewActionsBar` (all six action buttons, conditional
    justification/notes fields with client-side min-length validation mirrored
    from the backend) and `ReviewHistoryPanel` (full append-only history)
- `DiffViewer` — Monaco `DiffEditor` with an inline/split toggle
- `BulkReviewPage` — checkbox-driven table with three actions: bulk skip, bulk
  assign reviewer, bulk export approved patches (button labeled and restricted
  to `accepted`/`edited` violations only). No bulk-accept control exists.
- `AuditLogPage` — searchable, filterable view over `/audit-entries`
- `ReviewerIdentityBar` / `useReviewerStore` — lightweight, locally-persisted
  reviewer identity (id + display name) used to attribute every action. There
  is no authentication system yet (see Known Limitations); this is the
  documented stand-in until real auth lands.

## Justification Rules

| Action | Justification required? | Minimum length |
|--------|--------------------------|-----------------|
| accept | Yes | 20 characters |
| suppress | Yes | 20 characters |
| false_positive | Yes | 20 characters |
| reject | No | — |
| skip | No | — |
| edit | No (but `edited_fix.suggested_code` is required) | — |

Validation is enforced server-side (`ReviewService`, HTTP 422 on failure) and
mirrored client-side for immediate feedback. Justifications are stored in both
`violation_reviews.justification` and `audit_entries.justification`, and are
searchable via `GET /api/v1/audit-entries?q=...`.

## Patch Engine Behavior

- Patches are generated automatically the moment `accept` or `edit` is
  submitted — this is the "Patch Generation" step in the workflow diagram.
- Every patch has both a unified diff and a git-style patch (`diff --git a/... b/...`).
- `source_available=false` on a patch means the platform could not read the
  original file from disk (path outside the mounted project volume, or the
  file no longer exists) — the diff is then a best-effort textual
  substitution and is clearly flagged in the UI.
- Export endpoints and the bulk-export endpoint mark a patch `exported` and
  record who exported it and when — but never touch the filesystem being
  analyzed.

## Bulk Operations

| Operation | Effect |
|-----------|--------|
| Bulk Skip | Runs `skip` for every selected violation, no justification required |
| Bulk Assign Reviewer | Sets `assigned_reviewer_id/name`, logs one audit entry per violation plus a `bulk_operation` summary entry |
| Bulk Export Approved Patches | Only violations already `accepted` or `edited` are eligible; combines their latest patches into one downloadable bundle and marks each `exported` |
| Bulk Accept | **Does not exist.** No route, no service method, no UI control. |

## Known Limitations

1. No real authentication/authorization yet — reviewer identity is a
   self-reported, locally-persisted id/name pair (`useReviewerStore`),
   consistent with the stub `core/security.py` from Phase 1. Every audit row
   still records who performed the action, so the append-only trail itself is
   trustworthy; only the *proof* of identity is deferred.
2. Pilot rules from Phase 1.2 emit advisory/descriptive `suggested_code` text
   (e.g. "cast operands to a common essential type category") rather than
   literal compilable replacements. The patch engine treats whatever text the
   engineer accepts/edits as literal replacement lines, so patches for those
   pilot rules are most useful after the engineer edits the fix into real code
   via the `edit` action.
3. `SourceFileService` requires the analyzed project's `root_path` to be
   reachable from the backend's filesystem (as in Phase 1). If it isn't, the
   left panel and diff viewer fall back to the stored snippet/expression only.
4. Re-review is allowed (a violation can be reviewed more than once); the
   violation's `status` reflects only the *latest* action, while the full
   decision history remains in `violation_reviews` and `audit_entries`
   forever.
5. Combined bulk-export patch bundles are simple newline-joined concatenations
   of individual git patches — apply them one at a time if `git apply`
   rejects a multi-file bundle.

## User Workflow

1. Open a violation from `/violations` or `/projects/{id}/violations` → lands on `/violations/{id}/review`
2. Set your reviewer identity once (persisted locally)
3. Inspect source, explanation, rationale, confidence, and the suggested fix
4. Choose Accept / Reject / Edit / Skip / False Positive / Suppress
5. Provide a justification when required (accept/suppress/false_positive) and optional notes
6. On Accept/Edit, a patch is generated automatically — preview it, then export as `.patch` or `.diff`
7. Apply the exported patch manually outside the platform (e.g. `git apply file.patch`)
8. Inspect the full append-only history on the same page, or search across all decisions at `/audit-log`
9. For large batches, use `/projects/{id}/review/bulk` for skip / assign / export-approved (never bulk accept)

## Verification

```bash
cd backend && python -m pytest tests/unit/test_review_workflow.py -v
cd backend && python -m ruff check src tests
cd frontend && npm run typecheck && npm run lint && npm run build
```
