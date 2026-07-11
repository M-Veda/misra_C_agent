import { NavLink, Outlet } from "react-router-dom";

import { useHealthQuery } from "@/api/hooks/useHealthQuery";
import { StatusBadge } from "@/components/ui/StatusBadge";

const navigation = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/projects", label: "Projects", end: false },
  { to: "/rules", label: "Rule Catalog", end: false },
  { to: "/rules/coverage", label: "Coverage", end: true },
  { to: "/violations", label: "Violations", end: false },
  { to: "/audit-log", label: "Audit Log", end: true },
  { to: "/foundation", label: "Foundation", end: false },
] as const;

export function AppLayout() {
  const { data: health } = useHealthQuery();

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-64 flex-col border-r border-surface-border bg-surface-elevated">
        <div className="border-b border-surface-border px-6 py-5">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
            MISRA Platform
          </p>
          <h1 className="mt-1 text-lg font-semibold text-white">Compliance Console</h1>
        </div>

        <nav className="flex flex-1 flex-col gap-1 px-3 py-4">
          {navigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                isActive ? "nav-link nav-link-active" : "nav-link"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-surface-border px-6 py-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>API Status</span>
            <StatusBadge status={health?.status ?? "unknown"} />
          </div>
          <p className="mt-2 text-xs text-slate-500">v{health?.version ?? "—"}</p>
        </div>
      </aside>

      <main className="flex flex-1 flex-col">
        <header className="border-b border-surface-border bg-surface-elevated/60 px-8 py-4 backdrop-blur">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-400">Phase 9 Release Hardening</p>
              <h2 className="text-xl font-semibold text-white">MISRA Compliance Console</h2>
            </div>
            <div className="rounded-full border border-surface-border px-3 py-1 text-xs text-slate-300">
              Environment: {health?.environment ?? "connecting"}
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-auto p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
