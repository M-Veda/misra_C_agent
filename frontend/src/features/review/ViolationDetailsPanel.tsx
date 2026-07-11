import { Link } from "react-router-dom";

import type { RuleDetail, Violation } from "@/api/rulesClient";
import { StatusBadge } from "@/components/ui/StatusBadge";

interface ViolationDetailsPanelProps {
  violation: Violation;
  rule: RuleDetail | undefined;
}

export function ViolationDetailsPanel({ violation, rule }: ViolationDetailsPanelProps) {
  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto rounded-xl border border-surface-border bg-surface-elevated p-5">
      <div>
        <div className="flex items-center gap-2">
          <StatusBadge status={violation.severity} />
          <StatusBadge status={violation.category} />
          <span className="text-xs text-slate-500">{violation.rule_id}</span>
        </div>
        <h3 className="mt-2 text-base font-semibold text-white">
          {rule ? `Rule ${rule.rule_number}: ${rule.title}` : violation.rule_id}
        </h3>
      </div>

      <ConfidenceGauge score={violation.confidence_score} />

      <Section title="Explanation" text={violation.explanation} />
      <Section title="Risk Description" text={violation.risk_description} />
      {rule && <Section title="Rationale" text={rule.rationale} />}

      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">Offending Expression</p>
        <pre className="mt-1 overflow-x-auto rounded-lg bg-surface p-3 text-xs text-slate-300">
          {violation.offending_expression}
        </pre>
      </div>

      {violation.macro_expansion_chain_json && violation.macro_expansion_chain_json.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Macro Expansion Chain</p>
          <p className="mt-1 text-xs text-slate-400">
            {violation.macro_expansion_chain_json.join(" → ")}
          </p>
        </div>
      )}

      {rule && (
        <Link
          to={`/rules/${rule.rule_id}`}
          className="text-xs text-accent hover:underline"
          target="_blank"
        >
          View full rule metadata →
        </Link>
      )}
    </div>
  );
}

function Section({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-1 text-sm text-slate-300">{text}</p>
    </div>
  );
}

function ConfidenceGauge({ score }: { score: number }) {
  const percent = Math.round(score * 100);
  const color = percent >= 80 ? "bg-emerald-500" : percent >= 55 ? "bg-amber-500" : "bg-red-500";
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span className="uppercase tracking-wide">Detection Confidence</span>
        <span className="font-medium text-white">{percent}%</span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-surface">
        <div className={`h-full ${color} transition-all`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}
