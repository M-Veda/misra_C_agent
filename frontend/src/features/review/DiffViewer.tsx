import { DiffEditor, loader } from "@monaco-editor/react";
import { useState } from "react";

loader.config({
  paths: {
    vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs",
  },
});

interface DiffViewerProps {
  original: string;
  modified: string;
  height?: string;
}

export function DiffViewer({ original, modified, height = "220px" }: DiffViewerProps) {
  const [mode, setMode] = useState<"split" | "inline">("split");

  return (
    <div className="overflow-hidden rounded-xl border border-surface-border">
      <div className="flex items-center justify-between border-b border-surface-border bg-surface-elevated px-4 py-2">
        <span className="text-xs uppercase tracking-wide text-slate-500">Diff Preview</span>
        <div className="flex gap-1 rounded-lg bg-surface p-1">
          <button
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              mode === "split" ? "bg-accent text-white" : "text-slate-400"
            }`}
            onClick={() => setMode("split")}
          >
            Split
          </button>
          <button
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              mode === "inline" ? "bg-accent text-white" : "text-slate-400"
            }`}
            onClick={() => setMode("inline")}
          >
            Inline
          </button>
        </div>
      </div>
      <DiffEditor
        height={height}
        language="c"
        theme="vs-dark"
        original={original}
        modified={modified}
        options={{
          readOnly: true,
          renderSideBySide: mode === "split",
          minimap: { enabled: false },
          fontFamily: "JetBrains Mono, ui-monospace, monospace",
          fontSize: 13,
          scrollBeyondLastLine: false,
          automaticLayout: true,
        }}
      />
    </div>
  );
}
