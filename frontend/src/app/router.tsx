import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppLayout } from "@/app/layouts/AppLayout";
import { AnalysisProgressPage } from "@/features/analysis/AnalysisProgressPage";
import { ProjectsPage } from "@/features/analysis/ProjectsPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { FoundationPage } from "@/features/dashboard/FoundationPage";
import { ComplianceTrendsPage } from "@/features/enterprise/ComplianceTrendsPage";
import { TeamDashboardPage } from "@/features/enterprise/TeamDashboardPage";
import { RuleCatalogPage } from "@/features/rules/RuleCatalogPage";
import { RuleCoveragePage } from "@/features/rules/RuleCoveragePage";
import { RuleDetailPage } from "@/features/rules/RuleDetailPage";
import { AuditLogPage } from "@/features/review/AuditLogPage";
import { BulkReviewPage } from "@/features/review/BulkReviewPage";
import { ReviewWorkspacePage } from "@/features/review/ReviewWorkspacePage";
import { ViolationExplorerPage } from "@/features/violations/ViolationExplorerPage";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "foundation", element: <FoundationPage /> },
      { path: "projects", element: <ProjectsPage /> },
      { path: "projects/:projectId/analysis", element: <AnalysisProgressPage /> },
      { path: "projects/:projectId/violations", element: <ViolationExplorerPage /> },
      { path: "projects/:projectId/review/bulk", element: <BulkReviewPage /> },
      { path: "projects/:projectId/enterprise", element: <TeamDashboardPage /> },
      { path: "projects/:projectId/compliance-trends", element: <ComplianceTrendsPage /> },
      { path: "rules", element: <RuleCatalogPage /> },
      { path: "rules/coverage", element: <RuleCoveragePage /> },
      { path: "rules/:ruleId", element: <RuleDetailPage /> },
      { path: "violations", element: <ViolationExplorerPage /> },
      { path: "violations/:violationId/review", element: <ReviewWorkspacePage /> },
      { path: "audit-log", element: <AuditLogPage /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
