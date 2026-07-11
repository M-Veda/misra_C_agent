import { useEffect, useState } from "react";

interface AnalysisStreamEvent {
  event_type: string;
  analysis_run_id: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export function useAnalysisStream(runId: string | null) {
  const [events, setEvents] = useState<AnalysisStreamEvent[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!runId) {
      return;
    }

    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
    const source = new EventSource(`${baseUrl}/api/v1/analysis/runs/${runId}/stream`);

    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    source.addEventListener("progress", (event) => {
      const payload = JSON.parse(event.data) as AnalysisStreamEvent;
      setEvents((current) => [payload, ...current].slice(0, 100));
    });

    return () => {
      source.close();
      setConnected(false);
    };
  }, [runId]);

  return { events, connected };
}
