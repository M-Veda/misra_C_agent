import type { Patch } from "@/api/reviewClient";
import type { ImpactEstimate } from "@/api/reviewClient";
import type { Violation } from "@/api/rulesClient";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DiffViewer } from "@/features/review/DiffViewer";

interface SuggestedFix {
  original_code: string;
  suggested_code: string;
  rationale: string;
  confidence_score: number;
}

interface FixPanelProps {
  violation: Violation;
  impact: ImpactEstimate | undefined;
  isEditing: boolean;
  editedFixText: string;
  onEditedFixChange: (value: string) => void;
  latestPatch: Patch | undefined;
  onExportPatch: (patch: Patch, format: "git" | "unified") => void;
}

export function FixPanel({
  violation,
  impact,
  isEditing,
  editedFixText,
  onEditedFixChange,
  latestPatch,
  onExportPatch,
}: FixPanelProps) {
  const suggestedFix = violation.suggested_fix_json as SuggestedFix | null;
  const displayedFix = isEditing ? editedFixText : suggestedFix?.suggested_code ?? "";
  const original = suggestedFix?.original_code || violation.offending_expression;

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto rounded-xl border border-surface-border bg-surface-elevated p-5">
      {impact && (
        <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">Impact Estimate</p>
          <div className="mt-1 flex items-center gap-2">
            <StatusBadge status={impact.level} />
            <span className="text-sm text-slate-300">{impact.summary}</span>
          </div>
        </div>
      )}

      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">Suggested Fix</p>
        {suggestedFix ? (
          <>
            <p className="mt-1 text-sm text-slate-300">{suggestedFix.rationale}</p>
            <p className="mt-1 text-xs text-slate-500">
              Fix generator confidence: {Math.round(suggestedFix.confidence_score * 100)}%
            </p>
          </>
        ) : (
          <p className="mt-1 text-sm text-slate-500">No suggested fix was generated for this rule.</p>
        )}
      </div>

      {isEditing && (
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Editable Fix</p>
          <textarea
            className="mt-1 h-24 w-full rounded-lg border border-surface-border bg-surface p-3 font-mono text-xs text-white"
            value={editedFixText}
            onChange={(event) => onEditedFixChange(event.target.value)}
            placeholder="Write the corrected code the engineer wants to apply..."
          />
        </div>
      )}

      <DiffViewer original={original} modified={displayedFix || original} />

      {latestPatch && (
        <div>
          <div className="flex items-center justify-between">
            <p className="text-xs uppercase tracking-wide text-slate-500">Patch Preview</p>
            <StatusBadge status={latestPatch.status} />
          </div>
          {!latestPatch.source_available && (
            <p className="mt-1 text-xs text-amber-300">
              Original source file was not accessible — this is a best-effort textual patch, not a
              line-accurate diff. Review carefully before export.
            </p>
          )}
          <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-surface p-3 text-xs text-slate-300">
            {latestPatch.git_patch}
          </pre>
          <div className="mt-2 flex gap-2">
            <button
              className="rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white"
              onClick={() => onExportPatch(latestPatch, "git")}
            >
              Export .patch
            </button>
            <button
              className="rounded-lg border border-surface-border px-3 py-1.5 text-xs font-medium text-slate-300"
              onClick={() => onExportPatch(latestPatch, "unified")}
            >
              Export .diff
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Export only — the platform never applies this patch automatically. Apply it manually
            with <code>git apply</code> after review.
          </p>
        </div>
      )}
    </div>
  );
}
