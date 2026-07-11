import type { TranslationUnit } from "@/api/analysisClient";
import { StatusBadge } from "@/components/ui/StatusBadge";

interface TranslationUnitExplorerProps {
  translationUnits: TranslationUnit[];
  selectedTuId: string | null;
  onSelect: (tuId: string) => void;
}

export function TranslationUnitExplorer({
  translationUnits,
  selectedTuId,
  onSelect,
}: TranslationUnitExplorerProps) {
  return (
    <section className="panel p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
        Translation Units
      </h3>
      <div className="mt-4 max-h-[640px] space-y-2 overflow-auto">
        {translationUnits.map((unit) => (
          <button
            key={unit.id}
            type="button"
            onClick={() => onSelect(unit.id)}
            className={`w-full rounded-lg border px-3 py-3 text-left ${
              selectedTuId === unit.id
                ? "border-accent bg-accent/10"
                : "border-surface-border bg-surface hover:border-slate-500"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <p className="truncate text-sm font-medium text-white">{unit.file_path}</p>
              <StatusBadge status={unit.status === "completed" ? "healthy" : unit.status} />
            </div>
            <p className="mt-1 text-xs text-slate-400">
              {unit.node_count} nodes · {unit.parse_duration_ms} ms
            </p>
          </button>
        ))}
        {translationUnits.length === 0 && (
          <p className="text-sm text-slate-400">No translation units parsed yet.</p>
        )}
      </div>
    </section>
  );
}
