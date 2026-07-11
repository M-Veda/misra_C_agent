import Editor, { loader, type OnMount } from "@monaco-editor/react";
import { useRef } from "react";

loader.config({
  paths: {
    vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs",
  },
});

interface SourceCodePanelProps {
  filePath: string;
  lines: string[];
  startLine: number;
  highlightStart: number;
  highlightEnd: number;
  available: boolean;
}

export function SourceCodePanel({
  filePath,
  lines,
  startLine,
  highlightStart,
  highlightEnd,
  available,
}: SourceCodePanelProps) {
  const decorationIds = useRef<string[]>([]);

  const content = lines.join("\n");
  const relativeHighlightStart = highlightStart - startLine + 1;
  const relativeHighlightEnd = highlightEnd - startLine + 1;

  const handleMount: OnMount = (editor, monaco) => {
    decorationIds.current = editor.deltaDecorations(
      decorationIds.current,
      [
        {
          range: new monaco.Range(relativeHighlightStart, 1, relativeHighlightEnd, 1),
          options: {
            isWholeLine: true,
            className: "misra-violation-line",
            linesDecorationsClassName: "misra-violation-marker",
          },
        },
      ],
    );
    editor.revealLineInCenter(Math.max(relativeHighlightStart, 1));
  };

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-surface-border">
      <div className="border-b border-surface-border bg-surface-elevated px-4 py-2 text-xs text-slate-400">
        {filePath}
        {!available && (
          <span className="ml-2 rounded-full bg-amber-500/15 px-2 py-0.5 text-amber-300">
            source unavailable — showing snippet only
          </span>
        )}
      </div>
      <style>{`
        .misra-violation-line { background-color: rgba(239, 68, 68, 0.12); }
        .misra-violation-marker { background-color: #ef4444; width: 4px !important; margin-left: 4px; }
      `}</style>
      <Editor
        height="100%"
        language="c"
        theme="vs-dark"
        value={content || "// Source content not available for this file."}
        onMount={handleMount}
        options={{
          readOnly: true,
          minimap: { enabled: false },
          fontFamily: "JetBrains Mono, ui-monospace, monospace",
          fontSize: 13,
          lineNumbers: (lineNumber: number) => String(lineNumber + startLine - 1),
          scrollBeyondLastLine: false,
          automaticLayout: true,
          padding: { top: 12, bottom: 12 },
        }}
      />
    </div>
  );
}
