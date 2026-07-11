import { useQuery } from "@tanstack/react-query";

import { enterpriseClient } from "@/api/enterpriseClient";

export function useTeamDashboardQuery(projectId: string, teamId?: string) {
  return useQuery({
    queryKey: ["team-dashboard", projectId, teamId],
    queryFn: () => enterpriseClient.getTeamDashboard(projectId, teamId),
    enabled: Boolean(projectId),
  });
}

export function useComplianceTrendsQuery(projectId: string, teamId?: string) {
  return useQuery({
    queryKey: ["compliance-trends", projectId, teamId],
    queryFn: () => enterpriseClient.getComplianceTrends(projectId, teamId),
    enabled: Boolean(projectId),
  });
}

export function useTeamsQuery() {
  return useQuery({
    queryKey: ["teams"],
    queryFn: () => enterpriseClient.listTeams(),
  });
}
