import { Link } from "react-router-dom";

import { useRuleCatalogQuery, useRuleCoverageQuery } from "@/api/hooks/useRulesQuery";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function RuleCatalogPage() {
  const { data: catalog, isLoading } = useRuleCatalogQuery();
  const { data: coverage } = useRuleCoverageQuery();

  return (
    <div className="grid gap-6">
      <section className="panel p-6">
        <h3 className="text-lg font-semibold text-white">Rule Catalog</h3>
        <p className="mt-1 text-sm text-slate-400">
          Dynamically discovered MISRA rule plugins with manifest validation.
        </p>
        {coverage && (
          <div className="mt-4 grid gap-4 md:grid-cols-4">
            <Metric label="Implemented" value={String(coverage.total_rules)} />
            <Metric label="MISRA C:2012" value={String(coverage.by_standard.misra_c_2012 ?? 0)} />
            <Metric label="MISRA C:2023" value={String(coverage.by_standard.misra_c_2023 ?? 0)} />
            <Metric
              label="Required"
              value={String(coverage.by_category.required ?? 0)}
            />
          </div>
        )}
      </section>

      <section className="panel overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-surface-border bg-surface-elevated text-slate-400">
            <tr>
              <th className="px-4 py-3">Rule</th>
              <th className="px-4 py-3">Standard</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Title</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td className="px-4 py-6 text-slate-400" colSpan={5}>
                  Loading catalog...
                </td>
              </tr>
            )}
            {catalog?.map((rule) => (
              <tr key={rule.rule_id} className="border-b border-surface-border/60">
                <td className="px-4 py-3">
                  <Link className="text-accent hover:underline" to={`/rules/${rule.rule_id}`}>
                    {rule.rule_number}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-300">{rule.standard}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={rule.category} />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={rule.severity} />
                </td>
                <td className="px-4 py-3 text-slate-300">{rule.title}</td>
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
