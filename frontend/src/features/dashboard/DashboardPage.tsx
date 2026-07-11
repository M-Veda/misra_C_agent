import { useHealthQuery } from "@/api/hooks/useHealthQuery";

export function DashboardPage() {
  const { data: health, isLoading, isError } = useHealthQuery();

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <section className="panel p-6 lg:col-span-2">
        <h3 className="text-lg font-semibold text-white">Release Candidate 1.0.0-rc1</h3>
        <p className="mt-2 text-sm text-slate-400">
          Industrial validation complete. 6 embedded corpora, 0 crashes, Prometheus metrics,
          and Kubernetes/Helm deployment ready.
        </p>

        <dl className="mt-6 grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
            <dt className="text-xs uppercase tracking-wide text-slate-500">API</dt>
            <dd className="mt-1 text-sm font-medium text-white">
              {isLoading ? "Connecting" : isError ? "Unavailable" : health?.status}
            </dd>
          </div>
          <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
            <dt className="text-xs uppercase tracking-wide text-slate-500">Version</dt>
            <dd className="mt-1 text-sm font-medium text-white">{health?.version ?? "—"}</dd>
          </div>
          <div className="rounded-lg border border-surface-border bg-surface px-4 py-3">
            <dt className="text-xs uppercase tracking-wide text-slate-500">Environment</dt>
            <dd className="mt-1 text-sm font-medium text-white">
              {health?.environment ?? "—"}
            </dd>
          </div>
        </dl>
      </section>

      <section className="panel p-6">
        <h3 className="text-lg font-semibold text-white">Validation & Deployment</h3>
        <ul className="mt-4 space-y-3 text-sm text-slate-300">
          <li>6 industrial corpora validated (0 crashes)</li>
          <li>Prometheus + OpenTelemetry observability</li>
          <li>Helm chart + Kubernetes manifests</li>
          <li>Release docs + operator handbook</li>
        </ul>
      </section>
    </div>
  );
}
