import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useProjectViolationsQuery } from "@/api/hooks/useRulesQuery";
import {
  useBulkAssignReviewerMutation,
  useBulkExportPatchesMutation,
  useBulkSkipMutation,
} from "@/api/hooks/useReviewQuery";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useReviewerStore } from "@/stores/reviewerStore";

const APPROVED_STATUSES = new Set(["accepted", "edited"]);

export function BulkReviewPage() {
  const { projectId = "" } = useParams();
  const { reviewerId, reviewerName } = useReviewerStore();
  const { data: violations = [], isLoading } = useProjectViolationsQuery(projectId || null);

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [assignTargetId, setAssignTargetId] = useState("");
  const [assignTargetName, setAssignTargetName] = useState("");
  const [bulkNotes, setBulkNotes] = useState("");
  const [exportResult, setExportResult] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const bulkSkip = useBulkSkipMutation();
  const bulkAssign = useBulkAssignReviewerMutation();
  const bulkExport = useBulkExportPatchesMutation();

  const approvedCount = useMemo(
    () => violations.filter((v) => selected.has(v.id) && APPROVED_STATUSES.has(v.status)).length,
    [violations, selected],
  );

  const toggleSelected = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleAll = () => {
    setSelected((prev) =>
      prev.size === violations.length ? new Set() : new Set(violations.map((v) => v.id)),
    );
  };

  const handleBulkSkip = async () => {
    setMessage(null);
    const result = await bulkSkip.mutateAsync({
      violation_ids: Array.from(selected),
      reviewer_id: reviewerId,
      reviewer_name: reviewerName || null,
      notes: bulkNotes.trim() || null,
    });
    setMessage(`Skipped ${result.skipped_violation_ids.length} violation(s).`);
    setSelected(new Set());
  };

  const handleBulkAssign = async () => {
    setMessage(null);
    const result = await bulkAssign.mutateAsync({
      violation_ids: Array.from(selected),
      reviewer_id: assignTargetId,
      reviewer_name: assignTargetName || null,
      assigned_by: reviewerId,
    });
    setMessage(`Assigned ${result.assigned_violation_ids.length} violation(s) to ${assignTargetId}.`);
  };

  const handleBulkExport = async () => {
    setMessage(null);
    const result = await bulkExport.mutateAsync({
      violation_ids: Array.from(selected),
      exported_by: reviewerId,
    });
    setExportResult(result.combined_patch);
    setMessage(
      `Exported ${result.exported_patch_ids.length} approved patch(es). ` +
        `${result.skipped_violation_ids.length} violation(s) were not eligible (must be accepted or edited).`,
    );
  };

  const downloadExport = () => {
    if (!exportResult) return;
    const blob = new Blob([exportResult], { type: "text/x-patch" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${projectId}-approved-patches.patch`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="grid gap-6">
      <div>
        <Link to={`/projects/${projectId}/violations`} className="text-sm text-accent hover:underline">
          ← Back to project violations
        </Link>
        <h2 className="mt-1 text-xl font-semibold text-white">Bulk Review Operations</h2>
        <p className="mt-1 text-sm text-slate-400">
          Bulk skip, bulk assign, and bulk export are supported. Bulk accept is intentionally not
          available — every acceptance requires an individual engineer decision and justification.
        </p>
      </div>

      {!reviewerId && (
        <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-300">
          Set your reviewer identity on a violation review page before running bulk actions.
        </p>
      )}

      {message && (
        <p className="rounded-lg border border-surface-border bg-surface px-4 py-3 text-sm text-slate-300">
          {message}
        </p>
      )}

      <section className="panel overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-surface-border bg-surface-elevated text-slate-400">
            <tr>
              <th className="px-4 py-3">
                <input
                  type="checkbox"
                  checked={violations.length > 0 && selected.size === violations.length}
                  onChange={toggleAll}
                />
              </th>
              <th className="px-4 py-3">Rule</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Assigned Reviewer</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td className="px-4 py-6 text-slate-400" colSpan={5}>
                  Loading violations...
                </td>
              </tr>
            )}
            {violations.map((violation) => (
              <tr key={violation.id} className="border-b border-surface-border/60">
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selected.has(violation.id)}
                    onChange={() => toggleSelected(violation.id)}
                  />
                </td>
                <td className="px-4 py-3 text-slate-300">
                  <Link className="hover:underline" to={`/violations/${violation.id}/review`}>
                    {violation.rule_id}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-300">
                  {violation.file_path}:{violation.line_start}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={violation.status} />
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {violation.assigned_reviewer_name || violation.assigned_reviewer_id || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="panel p-5">
          <h3 className="font-semibold text-white">Bulk Skip</h3>
          <p className="mt-1 text-xs text-slate-500">{selected.size} violation(s) selected</p>
          <textarea
            className="mt-3 h-20 w-full rounded-lg border border-surface-border bg-surface p-2 text-sm text-white"
            placeholder="Optional notes"
            value={bulkNotes}
            onChange={(event) => setBulkNotes(event.target.value)}
          />
          <button
            className="mt-3 w-full rounded-lg bg-slate-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            disabled={selected.size === 0 || !reviewerId || bulkSkip.isPending}
            onClick={handleBulkSkip}
          >
            {bulkSkip.isPending ? "Skipping..." : "Bulk Skip"}
          </button>
        </div>

        <div className="panel p-5">
          <h3 className="font-semibold text-white">Bulk Assign Reviewer</h3>
          <p className="mt-1 text-xs text-slate-500">{selected.size} violation(s) selected</p>
          <input
            className="mt-3 w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-white"
            placeholder="Reviewer ID"
            value={assignTargetId}
            onChange={(event) => setAssignTargetId(event.target.value)}
          />
          <input
            className="mt-2 w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-white"
            placeholder="Reviewer display name (optional)"
            value={assignTargetName}
            onChange={(event) => setAssignTargetName(event.target.value)}
          />
          <button
            className="mt-3 w-full rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            disabled={selected.size === 0 || !assignTargetId.trim() || !reviewerId || bulkAssign.isPending}
            onClick={handleBulkAssign}
          >
            {bulkAssign.isPending ? "Assigning..." : "Bulk Assign"}
          </button>
        </div>

        <div className="panel p-5">
          <h3 className="font-semibold text-white">Bulk Export Approved Patches</h3>
          <p className="mt-1 text-xs text-slate-500">
            {approvedCount} of {selected.size} selected are accepted/edited and eligible
          </p>
          <button
            className="mt-3 w-full rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
            disabled={selected.size === 0 || !reviewerId || bulkExport.isPending}
            onClick={handleBulkExport}
          >
            {bulkExport.isPending ? "Exporting..." : "Bulk Export Patches"}
          </button>
          {exportResult && (
            <button
              className="mt-2 w-full rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-slate-300"
              onClick={downloadExport}
            >
              Download combined .patch
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
