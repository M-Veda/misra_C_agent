interface StatusBadgeProps {
  status: string;
}

const statusStyles: Record<string, string> = {
  healthy: "bg-emerald-500/15 text-emerald-300",
  ready: "bg-emerald-500/15 text-emerald-300",
  degraded: "bg-amber-500/15 text-amber-300",
  unknown: "bg-slate-500/15 text-slate-300",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const style = statusStyles[status] ?? statusStyles.unknown;

  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${style}`}>
      {status}
    </span>
  );
}
