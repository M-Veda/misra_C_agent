const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export interface TeamDashboard {
  project_id: string;
  team_id: string | null;
  violations_open: number;
  violations_resolved: number;
  violations_total: number;
  compliance_score: number;
  rules_executed: number;
  assigned_pending: number;
  trend_direction: string;
}

export interface ComplianceTrendPoint {
  captured_at: string;
  analysis_run_id: string;
  violations_total: number;
  violations_open: number;
  violations_resolved: number;
  compliance_score: number;
  rules_executed: number;
  metrics?: Record<string, unknown>;
}

export interface Team {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  members: Array<{
    id: string;
    team_id: string;
    user_id: string;
    display_name: string;
    email: string | null;
    role: string;
    created_at: string;
  }>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const enterpriseClient = {
  getTeamDashboard: (projectId: string, teamId?: string) => {
    const query = teamId ? `?team_id=${teamId}` : "";
    return request<TeamDashboard>(`/api/v1/projects/${projectId}/dashboard${query}`);
  },
  getComplianceTrends: (projectId: string, teamId?: string, limit = 30) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (teamId) params.set("team_id", teamId);
    return request<ComplianceTrendPoint[]>(
      `/api/v1/projects/${projectId}/compliance-trends?${params.toString()}`
    );
  },
  listTeams: () => request<Team[]>("/api/v1/teams"),
};
