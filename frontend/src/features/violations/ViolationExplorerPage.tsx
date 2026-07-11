import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  useProjectViolationsQuery,
  useRuleStatisticsQuery,
  useRunViolationsQuery,
} from "@/api/hooks/useRulesQuery";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function ViolationExplorerPage() {
  const { projectId = "", runId: routeRunId = "" } = useParams();
  const [runId, setRunId] = useState(routeRunId || "");
  const { data: runViolations } = useRunViolationsQuery(runId || null);
  const { data: projectViolations } = useProjectViolationsQuery(projectId || null);
  const { data: statistics } = useRuleStatisticsQuery(runId || null);

  const violations = runId ? runViolations : projectViolations;

  return (
    <div className="grid gap-6">
      <section className="panel p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-white">Violation Explorer</h3>
            <p className="mt-1 text-sm text-slate-400">
              Browse violations with confidence scores and stable fingerprints. Click a violation to
              open the review workspace.
            </p>
          </div>
          {projectId && (
            <Link
              to={`/projects/${projectId}/review/bulk`}
              className="rounded-lg border border-surface-border px-4 py-2 text-sm font-medium text-slate-300 hover:border-accent"
            >
              Bulk Review Operations
            </Link>
          )}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label className="text-sm text-slate-400" htmlFor="run-id">
            Filter by analysis run ID
          </label>
          <input
            id="run-id"
            className="rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm text-white"
            placeholder="Run UUID (optional)"
            value={runId}
            onChange={(event) => setRunId(event.target.value)}
          />
        </div>
        {statistics && (
          <div className="mt-4 grid gap-4 md:grid-cols-4">
            <Metric label="Violations" value={String(statistics.violations_total)} />
            <Metric label="Rules Executed" value={String(statistics.rules_executed)} />
            <Metric label="Duration (ms)" value={statistics.execution_duration_ms.toFixed(1)} />
            <Metric label="TUs Analyzed" value={String(statistics.translation_units_analyzed)} />
          </div>
        )}
      </section>

      <section className="panel overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-surface-border bg-surface-elevated text-slate-400">
            <tr>
              <th className="px-4 py-3">Rule</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Confidence</th>
              <th className="px-4 py-3">Fingerprint</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {!violations?.length && (
              <tr>
                <td className="px-4 py-6 text-slate-400" colSpan={6}>
                  No violations recorded yet. Run analysis on a project first.
                </td>
              </tr>
            )}
            {violations?.map((violation) => (
              <tr key={violation.id} className="border-b border-surface-border/60">
                <td className="px-4 py-3 text-slate-300">
                  <Link className="hover:underline" to={`/violations/${violation.id}/review`}>
                    {violation.rule_id}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-300">
                  <Link className="hover:underline" to={`/violations/${violation.id}/review`}>
                    {violation.file_path}:{violation.line_start}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={violation.severity} />
                </td>
                <td className="px-4 py-3 text-slate-300">
                  {(violation.confidence_score * 100).toFixed(0)}%
                </td>
                <td className="px-4 py-3 font-mono text-xs text-slate-500">
                  {violation.fingerprint.slice(0, 12)}…
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={violation.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}
