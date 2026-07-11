import { useParams } from "react-router-dom";

import { useTeamDashboardQuery, useTeamsQuery } from "@/api/hooks/useEnterpriseQuery";

export function TeamDashboardPage() {
  const { projectId = "" } = useParams();
  const { data: dashboard, isLoading, isError } = useTeamDashboardQuery(projectId);
  const { data: teams } = useTeamsQuery();

  if (!projectId) {
    return (
      <p className="text-sm text-slate-400">
        Select a project from the URL, e.g. <code>/projects/&lt;id&gt;/enterprise</code>.
      </p>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <section className="panel p-6 lg:col-span-2">
        <h3 className="text-lg font-semibold text-white">Team Compliance Dashboard</h3>
        <p className="mt-2 text-sm text-slate-400">
          Enterprise view with reviewer workload and compliance score trends.
        </p>

        {isLoading && <p className="mt-6 text-sm text-slate-400">Loading dashboard…</p>}
        {isError && <p className="mt-6 text-sm text-rose-400">Failed to load dashboard.</p>}

        {dashboard && (
          <dl className="mt-6 grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
              <dt className="text-xs uppercase tracking-wide text-slate-500">Compliance Score</dt>
              <dd className="mt-1 text-2xl font-semibold text-white">
                {dashboard.compliance_score.toFixed(1)}%
              </dd>
            </div>
            <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
              <dt className="text-xs uppercase tracking-wide text-slate-500">Open Violations</dt>
              <dd className="mt-1 text-2xl font-semibold text-white">{dashboard.violations_open}</dd>
            </div>
            <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
              <dt className="text-xs uppercase tracking-wide text-slate-500">Assigned Pending</dt>
              <dd className="mt-1 text-2xl font-semibold text-white">
                {dashboard.assigned_pending}
              </dd>
            </div>
            <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
              <dt className="text-xs uppercase tracking-wide text-slate-500">Resolved</dt>
              <dd className="mt-1 text-sm font-medium text-white">{dashboard.violations_resolved}</dd>
            </div>
            <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
              <dt className="text-xs uppercase tracking-wide text-slate-500">Total</dt>
              <dd className="mt-1 text-sm font-medium text-white">{dashboard.violations_total}</dd>
            </div>
            <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
              <dt className="text-xs uppercase tracking-wide text-slate-500">Trend</dt>
              <dd className="mt-1 text-sm font-medium capitalize text-white">
                {dashboard.trend_direction}
              </dd>
            </div>
          </dl>
        )}
      </section>

      <section className="panel p-6">
        <h3 className="text-lg font-semibold text-white">Teams</h3>
        <ul className="mt-4 space-y-3 text-sm text-slate-300">
          {(teams ?? []).map((team) => (
            <li key={team.id} className="rounded-lg border border-surface-border px-3 py-2">
              <p className="font-medium text-white">{team.name}</p>
              <p className="text-xs text-slate-500">{team.members.length} member(s)</p>
            </li>
          ))}
          {!teams?.length && <li className="text-slate-500">No teams configured yet.</li>}
        </ul>
      </section>
    </div>
  );
}
