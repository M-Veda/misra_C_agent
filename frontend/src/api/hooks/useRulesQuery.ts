import { useQuery } from "@tanstack/react-query";

import { rulesApi } from "@/api/rulesClient";

export function useRuleCatalogQuery() {
  return useQuery({
    queryKey: ["rules", "catalog"],
    queryFn: rulesApi.listCatalog,
  });
}

export function useRuleDetailQuery(ruleId: string | null) {
  return useQuery({
    queryKey: ["rules", "detail", ruleId],
    queryFn: () => rulesApi.getRule(ruleId!),
    enabled: Boolean(ruleId),
  });
}

export function useRuleCoverageQuery() {
  return useQuery({
    queryKey: ["rules", "coverage"],
    queryFn: rulesApi.getCoverage,
  });
}

export function useViolationQuery(violationId: string | null) {
  return useQuery({
    queryKey: ["violations", "detail", violationId],
    queryFn: () => rulesApi.getViolation(violationId!),
    enabled: Boolean(violationId),
  });
}

export function useRunViolationsQuery(runId: string | null) {
  return useQuery({
    queryKey: ["violations", "run", runId],
    queryFn: () => rulesApi.listRunViolations(runId!),
    enabled: Boolean(runId),
  });
}

export function useProjectViolationsQuery(projectId: string | null) {
  return useQuery({
    queryKey: ["violations", "project", projectId],
    queryFn: () => rulesApi.listProjectViolations(projectId!),
    enabled: Boolean(projectId),
  });
}

export function useRuleStatisticsQuery(runId: string | null) {
  return useQuery({
    queryKey: ["rules", "statistics", runId],
    queryFn: () => rulesApi.getRunStatistics(runId!),
    enabled: Boolean(runId),
  });
}
