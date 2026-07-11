import type { ReviewAction } from "@/api/reviewClient";

const MIN_JUSTIFICATION_LENGTH = 20;

const ACTIONS_REQUIRING_JUSTIFICATION: ReviewAction[] = ["accept", "suppress", "false_positive"];

const ACTION_LABELS: Record<ReviewAction, string> = {
  accept: "Accept Fix",
  reject: "Reject",
  edit: "Edit Fix",
  skip: "Skip",
  false_positive: "False Positive",
  suppress: "Suppress",
};

const ACTION_STYLES: Record<ReviewAction, string> = {
  accept: "bg-emerald-600 hover:bg-emerald-500",
  reject: "bg-red-600 hover:bg-red-500",
  edit: "bg-sky-600 hover:bg-sky-500",
  skip: "bg-slate-600 hover:bg-slate-500",
  false_positive: "bg-purple-600 hover:bg-purple-500",
  suppress: "bg-amber-600 hover:bg-amber-500",
};

interface ReviewActionsBarProps {
  pendingAction: ReviewAction | null;
  justification: string;
  notes: string;
  onJustificationChange: (value: string) => void;
  onNotesChange: (value: string) => void;
  onSelectAction: (action: ReviewAction) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  errorMessage: string | null;
  disabled: boolean;
}

export function ReviewActionsBar({
  pendingAction,
  justification,
  notes,
  onJustificationChange,
  onNotesChange,
  onSelectAction,
  onSubmit,
  isSubmitting,
  errorMessage,
  disabled,
}: ReviewActionsBarProps) {
  const requiresJustification = pendingAction
    ? ACTIONS_REQUIRING_JUSTIFICATION.includes(pendingAction)
    : false;
  const justificationOk = !requiresJustification || justification.trim().length >= MIN_JUSTIFICATION_LENGTH;

  return (
    <div className="rounded-xl border border-surface-border bg-surface-elevated p-5">
      <p className="text-xs uppercase tracking-wide text-slate-500">Review Decision</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {(Object.keys(ACTION_LABELS) as ReviewAction[]).map((action) => (
          <button
            key={action}
            disabled={disabled}
            className={`rounded-lg px-4 py-2 text-sm font-medium text-white transition-colors disabled:opacity-40 ${
              ACTION_STYLES[action]
            } ${pendingAction === action ? "ring-2 ring-white" : ""}`}
            onClick={() => onSelectAction(action)}
          >
            {ACTION_LABELS[action]}
          </button>
        ))}
      </div>

      {pendingAction && (
        <div className="mt-4 grid gap-3">
          <label className="text-sm text-slate-400">
            Justification{" "}
            {requiresJustification && (
              <span className="text-red-400">(required, min {MIN_JUSTIFICATION_LENGTH} chars)</span>
            )}
            <textarea
              className="mt-1 h-20 w-full rounded-lg border border-surface-border bg-surface p-3 text-sm text-white"
              value={justification}
              onChange={(event) => onJustificationChange(event.target.value)}
              placeholder="Explain the engineering reasoning behind this decision. Stored permanently and searchable."
            />
          </label>
          <label className="text-sm text-slate-400">
            Notes (optional)
            <textarea
              className="mt-1 h-16 w-full rounded-lg border border-surface-border bg-surface p-3 text-sm text-white"
              value={notes}
              onChange={(event) => onNotesChange(event.target.value)}
              placeholder="Any additional context for future reviewers..."
            />
          </label>

          {errorMessage && <p className="text-sm text-red-400">{errorMessage}</p>}

          <div>
            <button
              className="rounded-lg bg-white px-5 py-2 text-sm font-semibold text-slate-900 disabled:opacity-40"
              disabled={!justificationOk || isSubmitting}
              onClick={onSubmit}
            >
              {isSubmitting ? "Submitting..." : `Confirm ${ACTION_LABELS[pendingAction]}`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
