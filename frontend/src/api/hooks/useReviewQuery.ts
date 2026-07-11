import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { reviewApi, SubmitReviewPayload } from "@/api/reviewClient";

export function useViolationSourceQuery(violationId: string | null, context = 25) {
  return useQuery({
    queryKey: ["violations", violationId, "source", context],
    queryFn: () => reviewApi.getSource(violationId!, context),
    enabled: Boolean(violationId),
  });
}

export function useViolationImpactQuery(violationId: string | null) {
  return useQuery({
    queryKey: ["violations", violationId, "impact"],
    queryFn: () => reviewApi.getImpact(violationId!),
    enabled: Boolean(violationId),
  });
}

export function useViolationReviewsQuery(violationId: string | null) {
  return useQuery({
    queryKey: ["violations", violationId, "reviews"],
    queryFn: () => reviewApi.listReviews(violationId!),
    enabled: Boolean(violationId),
  });
}

export function useViolationPatchesQuery(violationId: string | null) {
  return useQuery({
    queryKey: ["violations", violationId, "patches"],
    queryFn: () => reviewApi.listPatches(violationId!),
    enabled: Boolean(violationId),
  });
}

export function useSubmitReviewMutation(violationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: SubmitReviewPayload) => reviewApi.submitReview(violationId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["violations", violationId, "reviews"] });
      queryClient.invalidateQueries({ queryKey: ["violations", violationId, "patches"] });
      queryClient.invalidateQueries({ queryKey: ["violations"] });
    },
  });
}

export function useAuditEntriesQuery(params: {
  entityType?: string;
  entityId?: string;
  action?: string;
  actorId?: string;
  q?: string;
}) {
  return useQuery({
    queryKey: ["audit-entries", params],
    queryFn: () => reviewApi.searchAuditEntries(params),
  });
}

export function useBulkSkipMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reviewApi.bulkSkip,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["violations"] });
    },
  });
}

export function useBulkAssignReviewerMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reviewApi.bulkAssignReviewer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["violations"] });
    },
  });
}

export function useBulkExportPatchesMutation() {
  return useMutation({
    mutationFn: reviewApi.bulkExportPatches,
  });
}
