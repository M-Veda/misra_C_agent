import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/api/client";

export function useHealthQuery() {
  return useQuery({
    queryKey: ["health"],
    queryFn: apiClient.getHealth,
    refetchInterval: 30_000,
  });
}

export function useReadinessQuery() {
  return useQuery({
    queryKey: ["readiness"],
    queryFn: apiClient.getReadiness,
    refetchInterval: 30_000,
  });
}
