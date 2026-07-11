const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export interface HealthResponse {
  status: "healthy";
  version: string;
  environment: string;
  timestamp: string;
}

export interface ReadinessResponse {
  status: "ready" | "degraded";
  checks: Record<
    string,
    {
      status: "up" | "down";
      latency_ms: number;
      message?: string;
    }
  >;
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const apiClient = {
  getHealth: () => request<HealthResponse>("/api/v1/health"),
  getReadiness: () => request<ReadinessResponse>("/api/v1/health/ready"),
};
