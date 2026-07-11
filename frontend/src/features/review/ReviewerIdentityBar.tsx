import { useState } from "react";

import { useReviewerStore } from "@/stores/reviewerStore";

export function ReviewerIdentityBar() {
  const { reviewerId, reviewerName, setReviewer } = useReviewerStore();
  const [editing, setEditing] = useState(!reviewerId);
  const [draftId, setDraftId] = useState(reviewerId);
  const [draftName, setDraftName] = useState(reviewerName);

  if (!editing) {
    return (
      <div className="flex items-center justify-between rounded-lg border border-surface-border bg-surface px-4 py-2 text-sm">
        <span className="text-slate-300">
          Reviewing as <span className="font-medium text-white">{reviewerName || reviewerId}</span>
        </span>
        <button
          className="text-xs text-accent hover:underline"
          onClick={() => setEditing(true)}
        >
          Switch reviewer
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border border-surface-border bg-surface px-4 py-3">
      <label className="text-sm text-slate-400">
        Reviewer ID
        <input
          className="mt-1 block w-48 rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white"
          value={draftId}
          placeholder="e.g. j.smith"
          onChange={(event) => setDraftId(event.target.value)}
        />
      </label>
      <label className="text-sm text-slate-400">
        Display Name
        <input
          className="mt-1 block w-48 rounded-lg border border-surface-border bg-surface-elevated px-3 py-2 text-sm text-white"
          value={draftName}
          placeholder="e.g. Jamie Smith"
          onChange={(event) => setDraftName(event.target.value)}
        />
      </label>
      <button
        className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        disabled={!draftId.trim()}
        onClick={() => {
          setReviewer(draftId.trim(), draftName.trim());
          setEditing(false);
        }}
      >
        Confirm identity
      </button>
    </div>
  );
}
