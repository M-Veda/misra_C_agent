import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import type { Patch, ReviewAction } from "@/api/reviewClient";
import { reviewApi } from "@/api/reviewClient";
import { useRuleDetailQuery, useViolationQuery } from "@/api/hooks/useRulesQuery";
import {
  useSubmitReviewMutation,
  useViolationImpactQuery,
  useViolationPatchesQuery,
  useViolationReviewsQuery,
  useViolationSourceQuery,
} from "@/api/hooks/useReviewQuery";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DiffViewer } from "@/features/review/DiffViewer";
import { FixPanel } from "@/features/review/FixPanel";
import { ReviewActionsBar } from "@/features/review/ReviewActionsBar";
import { ReviewHistoryPanel } from "@/features/review/ReviewHistoryPanel";
import { ReviewerIdentityBar } from "@/features/review/ReviewerIdentityBar";
import { SourceCodePanel } from "@/features/review/SourceCodePanel";
import { ViolationDetailsPanel } from "@/features/review/ViolationDetailsPanel";
import { useReviewerStore } from "@/stores/reviewerStore";

export function ReviewWorkspacePage() {
  const { violationId = "" } = useParams();
  const { reviewerId, reviewerName } = useReviewerStore();

  const { data: violation, isLoading } = useViolationQuery(violationId || null);
  const { data: rule } = useRuleDetailQuery(violation?.rule_id ?? null);
  const { data: source } = useViolationSourceQuery(violationId || null);
  const { data: impact } = useViolationImpactQuery(violationId || null);
  const { data: reviews = [] } = useViolationReviewsQuery(violationId || null);
  const { data: patches = [] } = useViolationPatchesQuery(violationId || null);
  const submitReview = useSubmitReviewMutation(violationId);

  const [pendingAction, setPendingAction] = useState<ReviewAction | null>(null);
  const [justification, setJustification] = useState("");
  const [notes, setNotes] = useState("");
  const [editedFixText, setEditedFixText] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (isLoading || !violation) {
    return <p className="text-slate-400">Loading violation...</p>;
  }

  const suggestedFix = violation.suggested_fix_json as {
    original_code?: string;
    suggested_code?: string;
    rationale?: string;
    confidence_score?: number;
  } | null;

  const latestPatch: Patch | undefined = patches[0];

  const handleSelectAction = (action: ReviewAction) => {
    setPendingAction(action);
    setErrorMessage(null);
    if (action === "edit" && !editedFixText) {
      setEditedFixText(suggestedFix?.suggested_code ?? "");
    }
  };

  const handleSubmit = async () => {
    if (!pendingAction || !reviewerId) {
      setErrorMessage("Set your reviewer identity before submitting a decision.");
      return;
    }
    setErrorMessage(null);
    try {
      await submitReview.mutateAsync({
        action: pendingAction,
        reviewer_id: reviewerId,
        reviewer_name: reviewerName || null,
        justification: justification.trim() || null,
        notes: notes.trim() || null,
        edited_fix:
          pendingAction === "edit"
            ? {
                original_code: suggestedFix?.original_code ?? violation.offending_expression,
                suggested_code: editedFixText,
                rationale: suggestedFix?.rationale ?? "Reviewer-edited fix.",
                confidence_score: 0.6,
              }
            : null,
      });
      setPendingAction(null);
      setJustification("");
      setNotes("");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to submit review.");
    }
  };

  const handleExportPatch = (patch: Patch, format: "git" | "unified") => {
    const url = reviewApi.exportPatchUrl(violationId, patch.id, reviewerId || "unknown", format);
    window.open(url, "_blank");
  };

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link to="/violations" className="text-sm text-accent hover:underline">
            ← Back to violations
          </Link>
          <h2 className="mt-1 text-xl font-semibold text-white">
            {violation.file_path}:{violation.line_start}
          </h2>
        </div>
        <StatusBadge status={violation.status} />
      </div>

      <ReviewerIdentityBar />

      <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr_1fr]">
        <div style={{ height: "480px" }}>
          <SourceCodePanel
            filePath={source?.file_path ?? violation.file_path}
            lines={source?.lines ?? []}
            startLine={source?.start_line ?? violation.line_start}
            highlightStart={source?.highlight_start ?? violation.line_start}
            highlightEnd={source?.highlight_end ?? violation.line_end}
            available={source?.available ?? false}
          />
        </div>

        <ViolationDetailsPanel violation={violation} rule={rule} />

        <FixPanel
          violation={violation}
          impact={impact}
          isEditing={pendingAction === "edit"}
          editedFixText={editedFixText}
          onEditedFixChange={setEditedFixText}
          latestPatch={latestPatch}
          onExportPatch={handleExportPatch}
        />
      </div>

      {pendingAction !== "edit" && (
        <details className="rounded-xl border border-surface-border bg-surface-elevated p-4">
          <summary className="cursor-pointer text-xs uppercase tracking-wide text-slate-500">
            Full-width diff preview
          </summary>
          <div className="mt-3">
            <DiffViewer
              original={suggestedFix?.original_code ?? violation.offending_expression}
              modified={suggestedFix?.suggested_code ?? violation.offending_expression}
              height="280px"
            />
          </div>
        </details>
      )}

      <ReviewActionsBar
        pendingAction={pendingAction}
        justification={justification}
        notes={notes}
        onJustificationChange={setJustification}
        onNotesChange={setNotes}
        onSelectAction={handleSelectAction}
        onSubmit={handleSubmit}
        isSubmitting={submitReview.isPending}
        errorMessage={errorMessage}
        disabled={submitReview.isPending}
      />

      <ReviewHistoryPanel reviews={reviews} />
    </div>
  );
}
