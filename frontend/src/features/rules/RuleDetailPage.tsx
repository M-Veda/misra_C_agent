import { Link, useParams } from "react-router-dom";

import { useRuleDetailQuery } from "@/api/hooks/useRulesQuery";
import { StatusBadge } from "@/components/ui/StatusBadge";

export function RuleDetailPage() {
  const { ruleId = "" } = useParams();
  const { data: rule, isLoading, error } = useRuleDetailQuery(ruleId);

  if (isLoading) {
    return <p className="text-slate-400">Loading rule metadata...</p>;
  }

  if (error || !rule) {
    return <p className="text-red-400">Rule not found.</p>;
  }

  return (
    <div className="grid gap-6">
      <section className="panel p-6">
        <Link className="text-sm text-accent hover:underline" to="/rules">
          ← Back to catalog
        </Link>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <h3 className="text-xl font-semibold text-white">
            Rule {rule.rule_number}: {rule.title}
          </h3>
          <StatusBadge status={rule.category} />
          <StatusBadge status={rule.severity} />
        </div>
        <p className="mt-2 text-sm text-slate-400">{rule.standard}</p>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="panel p-6">
          <h4 className="font-semibold text-white">Description</h4>
          <p className="mt-2 text-sm text-slate-300">{rule.description}</p>
          <h4 className="mt-6 font-semibold text-white">Rationale</h4>
          <p className="mt-2 text-sm text-slate-300">{rule.rationale}</p>
          <h4 className="mt-6 font-semibold text-white">AST Requirements</h4>
          <p className="mt-2 text-sm text-slate-300">{rule.requires_ast_nodes.join(", ")}</p>
        </section>

        <section className="panel p-6">
          <h4 className="font-semibold text-white">Examples</h4>
          <div className="mt-4 grid gap-4">
            <ExampleBlock title="Compliant" items={rule.examples.compliant} />
            <ExampleBlock title="Non-compliant" items={rule.examples.non_compliant} />
          </div>
        </section>
      </div>
    </div>
  );
}

function ExampleBlock({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{title}</p>
      {items.map((item) => (
        <pre
          key={item}
          className="mt-2 overflow-x-auto rounded-lg border border-surface-border bg-surface p-3 text-xs text-slate-300"
        >
          {item}
        </pre>
      ))}
    </div>
  );
}
