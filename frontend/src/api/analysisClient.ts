const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export interface Project {
  id: string;
  name: string;
  root_path: string;
  toolchain_profile_id: string;
  compile_commands_path: string | null;
  created_at: string;
  updated_at: string;
}

export interface AnalysisRun {
  id: string;
  project_id: string;
  run_type: string;
  status: string;
  files_total: number;
  files_parsed: number;
  files_failed: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface TranslationUnit {
  id: string;
  analysis_run_id: string;
  file_path: string;
  status: string;
  translation_unit_hash: string | null;
  node_count: number;
  parse_duration_ms: number;
  diagnostics_json: Array<Record<string, unknown>> | null;
  preprocessor_json: Record<string, unknown> | null;
  error_message: string | null;
}

export interface AstArtifact {
  translation_unit_id: string;
  file_path: string;
  translation_unit_hash: string;
  nodes: Array<Record<string, unknown>>;
  diagnostics: Array<Record<string, unknown>>;
  preprocessor: Record<string, unknown>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const analysisApi = {
  listProjects: () => request<Project[]>("/api/v1/projects"),
  createProject: (payload: {
    name: string;
    root_path: string;
    toolchain_profile_id: string;
    compile_commands_path: string | null;
  }) =>
    request<Project>("/api/v1/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  startAnalysisRun: (projectId: string, payload: { run_type: "full" | "incremental" }) =>
    request<AnalysisRun>(`/api/v1/projects/${projectId}/analysis/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  getAnalysisRun: (runId: string) => request<AnalysisRun>(`/api/v1/analysis/runs/${runId}`),
  listTranslationUnits: (runId: string) =>
    request<TranslationUnit[]>(`/api/v1/analysis/runs/${runId}/translation-units`),
  getAstArtifact: (runId: string, tuId: string) =>
    request<AstArtifact>(`/api/v1/analysis/runs/${runId}/translation-units/${tuId}/ast`),
};
