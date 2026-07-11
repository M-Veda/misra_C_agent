interface DiagnosticsPanelProps {
  events: Array<{
    event_type: string;
    timestamp: string;
    payload: Record<string, unknown>;
  }>;
  translationUnits: Array<{
    file_path: string;
    diagnostics_json: Array<Record<string, unknown>> | null;
    status: string;
  }>;
}

export function DiagnosticsPanel({ events, translationUnits }: DiagnosticsPanelProps) {
  const diagnostics = translationUnits.flatMap((unit) =>
    (unit.diagnostics_json ?? []).map((item) => ({
      file_path: unit.file_path,
      severity: String(item.severity ?? "note"),
      message: String(item.message ?? ""),
    })),
  );

  return (
    <section className="panel p-4">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">
        Parsing Diagnostics
      </h3>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-xs font-medium text-slate-500">Live Events</p>
          <div className="max-h-56 space-y-2 overflow-auto rounded-lg border border-surface-border bg-surface p-3">
            {events.map((event, index) => (
              <div key={`${event.timestamp}-${index}`} className="text-xs text-slate-300">
                <span className="text-slate-500">{event.event_type}</span>{" "}
                {JSON.stringify(event.payload)}
              </div>
            ))}
            {events.length === 0 && <p className="text-xs text-slate-500">Waiting for events...</p>}
          </div>
        </div>
        <div>
          <p className="mb-2 text-xs font-medium text-slate-500">Clang Diagnostics</p>
          <div className="max-h-56 space-y-2 overflow-auto rounded-lg border border-surface-border bg-surface p-3">
            {diagnostics.map((item, index) => (
              <div key={index} className="text-xs text-slate-300">
                <span className="font-medium text-amber-300">{item.severity}</span> {item.message}{" "}
                <span className="text-slate-500">({item.file_path})</span>
              </div>
            ))}
            {diagnostics.length === 0 && (
              <p className="text-xs text-slate-500">No diagnostics reported.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
