import { useParams } from "react-router-dom";

import { useComplianceTrendsQuery } from "@/api/hooks/useEnterpriseQuery";

export function ComplianceTrendsPage() {
  const { projectId = "" } = useParams();
  const { data: trends, isLoading, isError } = useComplianceTrendsQuery(projectId);

  if (!projectId) {
    return (
      <p className="text-sm text-slate-400">
        Open <code>/projects/&lt;id&gt;/compliance-trends</code> to view historical analytics.
      </p>
    );
  }

  return (
    <section className="panel p-6">
      <h3 className="text-lg font-semibold text-white">Compliance Trends</h3>
      <p className="mt-2 text-sm text-slate-400">
        Historical snapshots captured after each CI analysis run. Immutable audit trail preserved.
      </p>

      {isLoading && <p className="mt-6 text-sm text-slate-400">Loading trends…</p>}
      {isError && <p className="mt-6 text-sm text-rose-400">Failed to load trends.</p>}

      {trends && trends.length > 0 ? (
        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full text-left text-sm text-slate-300">
            <thead className="border-b border-surface-border text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Captured</th>
                <th className="px-3 py-2">Score</th>
                <th className="px-3 py-2">Open</th>
                <th className="px-3 py-2">Resolved</th>
                <th className="px-3 py-2">Total</th>
                <th className="px-3 py-2">Rules</th>
              </tr>
            </thead>
            <tbody>
              {trends.map((point) => (
                <tr key={point.analysis_run_id} className="border-b border-surface-border/60">
                  <td className="px-3 py-2">{new Date(point.captured_at).toLocaleString()}</td>
                  <td className="px-3 py-2">{point.compliance_score.toFixed(1)}%</td>
                  <td className="px-3 py-2">{point.violations_open}</td>
                  <td className="px-3 py-2">{point.violations_resolved}</td>
                  <td className="px-3 py-2">{point.violations_total}</td>
                  <td className="px-3 py-2">{point.rules_executed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        !isLoading && (
          <p className="mt-6 text-sm text-slate-500">
            No snapshots yet. CI plugins capture a snapshot after each analysis run.
          </p>
        )
      )}
    </section>
  );
}
