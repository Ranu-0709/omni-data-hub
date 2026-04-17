import clsx from "clsx";

interface KpiCardProps {
  title: string;
  value: string;
  change?: number;
  subtitle?: string;
}

export default function KpiCard({ title, value, change, subtitle }: KpiCardProps) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6">
      <p className="text-sm text-[var(--text-secondary)]">{title}</p>
      <p className="mt-2 text-3xl font-bold">{value}</p>
      {change !== undefined && (
        <p className={clsx("mt-1 text-sm font-medium", change >= 0 ? "text-green-500" : "text-red-500")}>
          {change >= 0 ? "↑" : "↓"} {Math.abs(change).toFixed(1)}%
        </p>
      )}
      {subtitle && <p className="mt-1 text-xs text-[var(--text-secondary)]">{subtitle}</p>}
    </div>
  );
}
