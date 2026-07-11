import { useRuleCoverageQuery } from "@/api/hooks/useRulesQuery";

export function RuleCoveragePage() {
  const { data: coverage, isLoading } = useRuleCoverageQuery();

  if (isLoading || !coverage) {
    return <p className="text-slate-400">Loading coverage dashboard...</p>;
  }

  return (
    <div className="grid gap-6">
      <section className="panel p-6">
        <h3 className="text-lg font-semibold text-white">Rule Coverage Dashboard</h3>
        <p className="mt-1 text-sm text-slate-400">
          Pilot phase coverage across MISRA C:2012 and MISRA C:2023 packs.
        </p>
        <p className="mt-4 text-3xl font-semibold text-white">{coverage.total_rules} rules</p>
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <CoverageCard title="By Standard" entries={coverage.by_standard} />
        <CoverageCard title="By Category" entries={coverage.by_category} />
      </div>

      <section className="panel p-6">
        <h4 className="font-semibold text-white">Implemented Rule IDs</h4>
        <ul className="mt-4 grid gap-2 md:grid-cols-2">
          {coverage.implemented_rule_ids.map((ruleId) => (
            <li
              key={ruleId}
              className="rounded-lg border border-surface-border px-3 py-2 text-sm text-slate-300"
            >
              {ruleId}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function CoverageCard({
  title,
  entries,
}: {
  title: string;
  entries: Record<string, number>;
}) {
  return (
    <section className="panel p-6">
      <h4 className="font-semibold text-white">{title}</h4>
      <div className="mt-4 grid gap-3">
        {Object.entries(entries).map(([key, value]) => (
          <div
            key={key}
            className="flex items-center justify-between rounded-lg bg-surface px-4 py-3"
          >
            <span className="text-sm text-slate-300">{key}</span>
            <span className="text-lg font-semibold text-white">{value}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
