import { useState } from "react";
import { useParams } from "react-router-dom";

import { useAnalysisStream } from "@/api/hooks/useAnalysisStream";
import {
  useAnalysisRunQuery,
  useStartAnalysisMutation,
  useTranslationUnitsQuery,
} from "@/api/hooks/useAnalysisQuery";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { AstExplorerPanel } from "@/features/analysis/AstExplorerPanel";
import { DiagnosticsPanel } from "@/features/analysis/DiagnosticsPanel";
import { TranslationUnitExplorer } from "@/features/analysis/TranslationUnitExplorer";

export function AnalysisProgressPage() {
  const { projectId = "" } = useParams();
  const [runId, setRunId] = useState<string | null>(null);
  const [selectedTuId, setSelectedTuId] = useState<string | null>(null);
  const startAnalysis = useStartAnalysisMutation(projectId);
  const { data: run } = useAnalysisRunQuery(runId);
  const { data: translationUnits } = useTranslationUnitsQuery(runId);
  const { events, connected } = useAnalysisStream(runId);

  const handleStart = async () => {
    const created = await startAnalysis.mutateAsync({ run_type: "full" });
    setRunId(created.id);
  };

  const progress =
    run && run.files_total > 0 ? Math.round((run.files_parsed / run.files_total) * 100) : 0;

  return (
    <div className="grid gap-6">
      <section className="panel p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">Analysis Progress</h3>
            <p className="mt-1 text-sm text-slate-400">
              Live Clang LibTooling parsing with SSE progress updates.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={connected ? "healthy" : "unknown"} />
            <button
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white"
              onClick={handleStart}
              disabled={startAnalysis.isPending}
            >
              {startAnalysis.isPending ? "Starting..." : "Start Analysis"}
            </button>
          </div>
        </div>

        {run && (
          <div className="mt-6 grid gap-4 md:grid-cols-4">
            <Metric label="Status" value={run.status} />
            <Metric label="Progress" value={`${progress}%`} />
            <Metric label="Parsed" value={`${run.files_parsed}/${run.files_total}`} />
            <Metric label="Failed" value={String(run.files_failed)} />
          </div>
        )}

        {run && (
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-surface">
            <div className="h-full bg-accent transition-all" style={{ width: `${progress}%` }} />
          </div>
        )}
      </section>

      <div className="grid gap-6 xl:grid-cols-[360px_1fr]">
        <TranslationUnitExplorer
          translationUnits={translationUnits ?? []}
          selectedTuId={selectedTuId}
          onSelect={setSelectedTuId}
        />
        <div className="grid gap-6">
          <DiagnosticsPanel events={events} translationUnits={translationUnits ?? []} />
          <AstExplorerPanel runId={runId} tuId={selectedTuId} />
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-medium capitalize text-white">{value}</p>
    </div>
  );
}
