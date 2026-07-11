const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export type ReviewAction =
  | "accept"
  | "reject"
  | "edit"
  | "skip"
  | "false_positive"
  | "suppress";

export interface EditedFixPayload {
  original_code: string;
  suggested_code: string;
  rationale: string;
  confidence_score: number;
}

export interface ViolationReview {
  id: string;
  violation_id: string;
  action: ReviewAction;
  previous_status: string;
  new_status: string;
  reviewer_id: string;
  reviewer_name: string | null;
  justification: string | null;
  notes: string | null;
  edited_fix_json: EditedFixPayload | null;
  created_at: string;
}

export interface Patch {
  id: string;
  violation_id: string;
  review_id: string;
  file_path: string;
  unified_diff: string;
  git_patch: string;
  source_available: boolean;
  confidence_score: number;
  status: "generated" | "exported";
  created_by: string;
  created_at: string;
  exported_at: string | null;
  exported_by: string | null;
}

export interface AuditEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor_id: string;
  actor_name: string | null;
  old_state_json: Record<string, unknown> | null;
  new_state_json: Record<string, unknown> | null;
  justification: string | null;
  notes: string | null;
  created_at: string;
}

export interface SubmitReviewResponse {
  review: ViolationReview;
  audit_entry: AuditEntry;
  patch: Patch | null;
  violation_status: string;
}

export interface SourceWindow {
  file_path: string;
  start_line: number;
  end_line: number;
  lines: string[];
  highlight_start: number;
  highlight_end: number;
  available: boolean;
}

export interface ImpactEstimate {
  level: "low" | "medium" | "high";
  score: number;
  summary: string;
}

export interface BulkSkipResponse {
  skipped_violation_ids: string[];
  not_found_violation_ids: string[];
}

export interface BulkAssignReviewerResponse {
  assigned_violation_ids: string[];
  not_found_violation_ids: string[];
}

export interface BulkExportPatchesResponse {
  combined_patch: string;
  exported_patch_ids: string[];
  skipped_violation_ids: string[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export interface SubmitReviewPayload {
  action: ReviewAction;
  reviewer_id: string;
  reviewer_name?: string | null;
  justification?: string | null;
  notes?: string | null;
  edited_fix?: EditedFixPayload | null;
}

export const reviewApi = {
  submitReview: (violationId: string, payload: SubmitReviewPayload) =>
    request<SubmitReviewResponse>(`/api/v1/violations/${violationId}/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  listReviews: (violationId: string) =>
    request<ViolationReview[]>(`/api/v1/violations/${violationId}/reviews`),
  listPatches: (violationId: string) =>
    request<Patch[]>(`/api/v1/violations/${violationId}/patches`),
  getSource: (violationId: string, context = 25) =>
    request<SourceWindow>(`/api/v1/violations/${violationId}/source?context=${context}`),
  getImpact: (violationId: string) =>
    request<ImpactEstimate>(`/api/v1/violations/${violationId}/impact`),
  exportPatchUrl: (violationId: string, patchId: string, exportedBy: string, format: "git" | "unified") =>
    `${API_BASE_URL}/api/v1/violations/${violationId}/patches/${patchId}/export?exported_by=${encodeURIComponent(
      exportedBy,
    )}&format=${format}`,
  searchAuditEntries: (params: {
    entityType?: string;
    entityId?: string;
    action?: string;
    actorId?: string;
    q?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams();
    if (params.entityType) query.set("entity_type", params.entityType);
    if (params.entityId) query.set("entity_id", params.entityId);
    if (params.action) query.set("action", params.action);
    if (params.actorId) query.set("actor_id", params.actorId);
    if (params.q) query.set("q", params.q);
    if (params.limit) query.set("limit", String(params.limit));
    if (params.offset) query.set("offset", String(params.offset));
    return request<AuditEntry[]>(`/api/v1/audit-entries?${query.toString()}`);
  },
  bulkSkip: (payload: {
    violation_ids: string[];
    reviewer_id: string;
    reviewer_name?: string | null;
    notes?: string | null;
  }) =>
    request<BulkSkipResponse>("/api/v1/violations/bulk/skip", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  bulkAssignReviewer: (payload: {
    violation_ids: string[];
    reviewer_id: string;
    reviewer_name?: string | null;
    assigned_by: string;
  }) =>
    request<BulkAssignReviewerResponse>("/api/v1/violations/bulk/assign-reviewer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  bulkExportPatches: (payload: { violation_ids: string[]; exported_by: string }) =>
    request<BulkExportPatchesResponse>("/api/v1/violations/bulk/export-patches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
};
