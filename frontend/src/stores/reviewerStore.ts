import { create } from "zustand";
import { persist } from "zustand/middleware";

interface ReviewerState {
  reviewerId: string;
  reviewerName: string;
  setReviewer: (reviewerId: string, reviewerName: string) => void;
}

export const useReviewerStore = create<ReviewerState>()(
  persist(
    (set) => ({
      reviewerId: "",
      reviewerName: "",
      setReviewer: (reviewerId, reviewerName) => set({ reviewerId, reviewerName }),
    }),
    {
      name: "misra-reviewer-identity",
    },
  ),
);
