import { ReactNode } from "react";

interface ChartCardProps {
  title: string;
  children: ReactNode;
  className?: string;
}

export default function ChartCard({ title, children, className = "" }: ChartCardProps) {
  return (
    <div className={`rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6 ${className}`}>
      <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-4">{title}</h3>
      {children}
    </div>
  );
}
