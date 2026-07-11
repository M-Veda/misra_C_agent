import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { analysisApi } from "@/api/analysisClient";

export function useProjectsQuery() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: analysisApi.listProjects,
  });
}

export function useCreateProjectMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: analysisApi.createProject,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useAnalysisRunQuery(runId: string | null) {
  return useQuery({
    queryKey: ["analysis-run", runId],
    queryFn: () => analysisApi.getAnalysisRun(runId!),
    enabled: Boolean(runId),
    refetchInterval: (query) =>
      query.state.data?.status === "running" || query.state.data?.status === "queued"
        ? 2000
        : false,
  });
}

export function useTranslationUnitsQuery(runId: string | null) {
  return useQuery({
    queryKey: ["translation-units", runId],
    queryFn: () => analysisApi.listTranslationUnits(runId!),
    enabled: Boolean(runId),
    refetchInterval: 3000,
  });
}

export function useAstArtifactQuery(runId: string | null, tuId: string | null) {
  return useQuery({
    queryKey: ["ast-artifact", runId, tuId],
    queryFn: () => analysisApi.getAstArtifact(runId!, tuId!),
    enabled: Boolean(runId && tuId),
  });
}

export function useStartAnalysisMutation(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { run_type: "full" | "incremental" }) =>
      analysisApi.startAnalysisRun(projectId, payload),
    onSuccess: (run) => {
      void queryClient.invalidateQueries({ queryKey: ["analysis-run", run.id] });
    },
  });
}
