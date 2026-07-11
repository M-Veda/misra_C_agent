import Editor, { loader } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { useMemo } from "react";

import { cn } from "@/lib/utils";

loader.config({
  paths: {
    vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs",
  },
});

const defaultOptions: editor.IStandaloneEditorConstructionOptions = {
  minimap: { enabled: false },
  fontFamily: "JetBrains Mono, ui-monospace, monospace",
  fontSize: 13,
  lineNumbers: "on",
  scrollBeyondLastLine: false,
  automaticLayout: true,
  readOnly: true,
  padding: { top: 16, bottom: 16 },
};

interface CodeEditorProps {
  value: string;
  language?: string;
  height?: string;
  className?: string;
  readOnly?: boolean;
}

export function CodeEditor({
  value,
  language = "c",
  height = "320px",
  className,
  readOnly = true,
}: CodeEditorProps) {
  const options = useMemo(
    () => ({
      ...defaultOptions,
      readOnly,
    }),
    [readOnly],
  );

  return (
    <div className={cn("overflow-hidden rounded-xl border border-surface-border", className)}>
      <Editor
        height={height}
        language={language}
        theme="vs-dark"
        value={value}
        options={options}
      />
    </div>
  );
}
