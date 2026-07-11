import { useReadinessQuery } from "@/api/hooks/useHealthQuery";
import { CodeEditor } from "@/components/code-editor/CodeEditor";
import { StatusBadge } from "@/components/ui/StatusBadge";

const sampleSource = `#include <stdint.h>

uint16_t calculate_rpm(uint16_t pulses, uint16_t window_ms)
{
    if (window_ms == 0U) {
        return 0U;
    }
    return (uint16_t)((pulses * 60000U) / window_ms);
}
`;

export function FoundationPage() {
  const { data: readiness, isLoading } = useReadinessQuery();

  return (
    <div className="grid gap-6">
      <section className="panel p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">Service Readiness</h3>
            <p className="mt-1 text-sm text-slate-400">
              Dependency checks against PostgreSQL, Redis, and the Clang worker.
            </p>
          </div>
          <StatusBadge status={readiness?.status ?? (isLoading ? "unknown" : "degraded")} />
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-3">
          {readiness &&
            Object.entries(readiness.checks).map(([name, check]) => (
              <div
                key={name}
                className="rounded-lg border border-surface-border bg-surface px-4 py-3"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium capitalize text-white">{name}</p>
                  <StatusBadge status={check.status === "up" ? "healthy" : "degraded"} />
                </div>
                <p className="mt-2 text-xs text-slate-400">{check.latency_ms} ms</p>
                {check.message && (
                  <p className="mt-1 truncate text-xs text-slate-500">{check.message}</p>
                )}
              </div>
            ))}
        </div>
      </section>

      <section className="panel p-6">
        <h3 className="text-lg font-semibold text-white">Monaco Editor Foundation</h3>
        <p className="mt-1 text-sm text-slate-400">
          Embedded code surface prepared for violation review workflows in Phase 2.
        </p>
        <div className="mt-4">
          <CodeEditor value={sampleSource} />
        </div>
      </section>
    </div>
  );
}
