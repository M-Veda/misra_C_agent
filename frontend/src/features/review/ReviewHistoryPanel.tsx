import type { ViolationReview } from "@/api/reviewClient";
import { StatusBadge } from "@/components/ui/StatusBadge";

interface ReviewHistoryPanelProps {
  reviews: ViolationReview[];
}

export function ReviewHistoryPanel({ reviews }: ReviewHistoryPanelProps) {
  return (
    <div className="rounded-xl border border-surface-border bg-surface-elevated p-5">
      <p className="text-xs uppercase tracking-wide text-slate-500">
        Review History — immutable, append-only audit trail
      </p>
      {reviews.length === 0 && (
        <p className="mt-3 text-sm text-slate-500">No review actions recorded yet.</p>
      )}
      <div className="mt-3 space-y-3">
        {reviews
          .slice()
          .reverse()
          .map((review) => (
            <div
              key={review.id}
              className="rounded-lg border border-surface-border bg-surface px-4 py-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <StatusBadge status={review.action} />
                  <span className="text-sm text-white">
                    {review.reviewer_name || review.reviewer_id}
                  </span>
                  <span className="text-xs text-slate-500">
                    {review.previous_status} → {review.new_status}
                  </span>
                </div>
                <span className="text-xs text-slate-500">
                  {new Date(review.created_at).toLocaleString()}
                </span>
              </div>
              {review.justification && (
                <p className="mt-2 text-sm text-slate-300">
                  <span className="text-slate-500">Justification: </span>
                  {review.justification}
                </p>
              )}
              {review.notes && (
                <p className="mt-1 text-sm text-slate-400">
                  <span className="text-slate-500">Notes: </span>
                  {review.notes}
                </p>
              )}
              {review.edited_fix_json && (
                <pre className="mt-2 overflow-x-auto rounded bg-surface-elevated p-2 text-xs text-slate-300">
                  {review.edited_fix_json.suggested_code}
                </pre>
              )}
            </div>
          ))}
      </div>
    </div>
  );
}
