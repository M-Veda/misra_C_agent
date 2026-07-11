import { useMemo, useState } from "react";

import { useAstArtifactQuery } from "@/api/hooks/useAnalysisQuery";
import { CodeEditor } from "@/components/code-editor/CodeEditor";

interface AstExplorerPanelProps {
  runId: string | null;
  tuId: string | null;
}

export function AstExplorerPanel({ runId, tuId }: AstExplorerPanelProps) {
  const { data: artifact, isLoading } = useAstArtifactQuery(runId, tuId);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const selectedNode = useMemo(
    () => artifact?.nodes.find((node) => node.node_id === selectedNodeId) ?? null,
    [artifact, selectedNodeId],
  );

  if (!tuId) {
    return (
      <section className="panel p-6">
        <p className="text-sm text-slate-400">Select a translation unit to inspect AST nodes.</p>
      </section>
    );
  }

  return (
    <section className="panel p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">AST Explorer</h3>
      {isLoading && <p className="mt-4 text-sm text-slate-400">Loading AST artifact...</p>}
      {artifact && (
        <div className="mt-4 grid gap-4 xl:grid-cols-[320px_1fr]">
          <div className="max-h-[520px] overflow-auto rounded-lg border border-surface-border bg-surface p-3">
            {artifact.nodes.map((node) => (
              <button
                key={String(node.node_id)}
                type="button"
                onClick={() => setSelectedNodeId(String(node.node_id))}
                className={`mb-2 block w-full rounded px-2 py-1 text-left text-xs ${
                  selectedNodeId === node.node_id
                    ? "bg-accent/20 text-white"
                    : "text-slate-300 hover:bg-surface-border"
                }`}
              >
                <span className="font-mono text-accent">{String(node.node_kind)}</span>
                <span className="ml-2 text-slate-500">{String(node.essential_type)}</span>
              </button>
            ))}
          </div>

          <div className="space-y-4">
            {selectedNode && (
              <div className="rounded-lg border border-surface-border bg-surface p-4 text-sm text-slate-300">
                <p>
                  <span className="text-slate-500">Kind:</span> {String(selectedNode.node_kind)}
                </p>
                <p>
                  <span className="text-slate-500">Essential Type:</span>{" "}
                  {String(selectedNode.essential_type)}
                </p>
                <p>
                  <span className="text-slate-500">Parent:</span> {String(selectedNode.parent_id)}
                </p>
              </div>
            )}

            <MacroIncludePanel preprocessor={artifact.preprocessor} />
            <CodeEditor
              value={JSON.stringify(selectedNode ?? artifact.nodes.slice(0, 3), null, 2)}
              language="json"
              height="280px"
            />
          </div>
        </div>
      )}
    </section>
  );
}

function MacroIncludePanel({ preprocessor }: { preprocessor: Record<string, unknown> }) {
  const macros = (preprocessor.macro_definitions as Array<Record<string, unknown>>) ?? [];
  const includes = (preprocessor.include_directives as Array<Record<string, unknown>>) ?? [];
  const conditionals =
    (preprocessor.conditional_branches as Array<Record<string, unknown>>) ?? [];

  return (
    <div className="grid gap-3 md:grid-cols-3">
      <InfoList title="Macros" items={macros.map((item) => String(item.name))} />
      <InfoList title="Includes" items={includes.map((item) => String(item.included_file))} />
      <InfoList
        title="Conditionals"
        items={conditionals.map((item) => `${item.directive}: ${item.condition}`)}
      />
    </div>
  );
}

function InfoList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-lg border border-surface-border bg-surface p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <ul className="mt-2 max-h-28 space-y-1 overflow-auto text-xs text-slate-300">
        {items.map((item, index) => (
          <li key={`${item}-${index}`}>{item}</li>
        ))}
        {items.length === 0 && <li className="text-slate-500">None</li>}
      </ul>
    </div>
  );
}
