import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuditEntriesQuery } from "@/api/hooks/useReviewQuery";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function AuditLogPage() {
  const [query, setQuery] = useState("");
  const [action, setAction] = useState("");
  const { data: entries = [], isLoading } = useAuditEntriesQuery({
    q: query || undefined,
    action: action || undefined,
  });

  return (
    <div className="grid gap-6">
      <section className="panel p-6">
        <h3 className="text-lg font-semibold text-white">Audit Trail</h3>
        <p className="mt-1 text-sm text-slate-400">
          Immutable, append-only log of every review decision, patch generation, and bulk operation.
          Justifications are stored permanently and are fully searchable.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <input
            className="w-64 rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-white"
            placeholder="Search justification or notes..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <select
            className="rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-white"
            value={action}
            onChange={(event) => setAction(event.target.value)}
          >
            <option value="">All actions</option>
            <option value="review.accept">Accept</option>
            <option value="review.reject">Reject</option>
            <option value="review.edit">Edit</option>
            <option value="review.skip">Skip</option>
            <option value="review.false_positive">False Positive</option>
            <option value="review.suppress">Suppress</option>
            <option value="patch.generated">Patch Generated</option>
            <option value="assign_reviewer">Assign Reviewer</option>
            <option value="bulk_skip">Bulk Skip</option>
            <option value="bulk_assign_reviewer">Bulk Assign Reviewer</option>
            <option value="bulk_export_patches">Bulk Export Patches</option>
          </select>
        </div>
      </section>

      <section className="panel overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-surface-border bg-surface-elevated text-slate-400">
            <tr>
              <th className="px-4 py-3">When</th>
              <th className="px-4 py-3">Who</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">Entity</th>
              <th className="px-4 py-3">Justification / Notes</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td className="px-4 py-6 text-slate-400" colSpan={5}>
                  Loading audit entries...
                </td>
              </tr>
            )}
            {!isLoading && entries.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-slate-400" colSpan={5}>
                  No audit entries match this search.
                </td>
              </tr>
            )}
            {entries.map((entry) => (
              <tr key={entry.id} className="border-b border-surface-border/60 align-top">
                <td className="px-4 py-3 text-xs text-slate-400">
                  {new Date(entry.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-slate-300">{entry.actor_name || entry.actor_id}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={entry.action} />
                </td>
                <td className="px-4 py-3 text-xs text-slate-400">
                  {entry.entity_type === "violation" ? (
                    <Link className="hover:underline" to={`/violations/${entry.entity_id}/review`}>
                      {entry.entity_type}:{entry.entity_id.slice(0, 8)}…
                    </Link>
                  ) : (
                    `${entry.entity_type}:${entry.entity_id.slice(0, 12)}…`
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-slate-300">
                  {entry.justification || entry.notes || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
