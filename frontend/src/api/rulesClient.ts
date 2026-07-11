const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export interface RuleMetadata {
  rule_id: string;
  rule_number: string;
  standard: string;
  category: string;
  severity: string;
  title: string;
  description: string;
  rationale: string;
  tags: string[];
  references: string[];
  plugin_module: string;
  plugin_version: string;
  requires_ast_nodes: string[];
}

export interface RuleDetail extends RuleMetadata {
  examples: {
    compliant: string[];
    non_compliant: string[];
  };
}

export interface RuleCoverage {
  total_rules: number;
  by_standard: Record<string, number>;
  by_category: Record<string, number>;
  implemented_rule_ids: string[];
}

export interface Violation {
  id: string;
  analysis_run_id: string;
  translation_unit_id: string | null;
  project_id: string;
  rule_id: string;
  fingerprint: string;
  file_path: string;
  line_start: number;
  line_end: number;
  column_start: number;
  column_end: number;
  severity: string;
  confidence_score: number;
  category: string;
  offending_expression: string;
  explanation: string;
  risk_description: string;
  source_snippet: string;
  ast_node_reference: string;
  macro_expansion_chain_json: string[] | null;
  suggested_fix_json: Record<string, unknown> | null;
  confidence_factors_json: Record<string, number> | null;
  status: string;
  assigned_reviewer_id: string | null;
  assigned_reviewer_name: string | null;
  first_seen_at: string;
  last_seen_at: string;
}

export interface RuleRunStatistics {
  analysis_run_id: string;
  rules_executed: number;
  violations_total: number;
  violations_deduplicated: number;
  execution_duration_ms: number;
  translation_units_analyzed: number;
  metrics_json: Record<string, unknown> | null;
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const rulesApi = {
  listCatalog: () => request<RuleMetadata[]>("/api/v1/rules/catalog"),
  getRule: (ruleId: string) => request<RuleDetail>(`/api/v1/rules/catalog/${ruleId}`),
  getCoverage: () => request<RuleCoverage>("/api/v1/rules/catalog/coverage"),
  getViolation: (violationId: string) => request<Violation>(`/api/v1/violations/${violationId}`),
  listRunViolations: (runId: string) =>
    request<Violation[]>(`/api/v1/analysis/runs/${runId}/violations`),
  listProjectViolations: (projectId: string) =>
    request<Violation[]>(`/api/v1/projects/${projectId}/violations`),
  getRunStatistics: (runId: string) =>
    request<RuleRunStatistics>(`/api/v1/analysis/runs/${runId}/rule-statistics`),
};
