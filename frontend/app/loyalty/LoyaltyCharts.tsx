"use client";

import { DonutChart, SimpleBarChart } from "@/components/charts/Charts";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";

interface Props {
  type: "donut" | "bar" | "line";
  data: Record<string, unknown>[];
}

export default function LoyaltyCharts({ type, data }: Props) {
  if (type === "donut") {
    return <DonutChart data={data} dataKey="value" nameKey="name" />;
  }
  if (type === "bar") {
    return <SimpleBarChart data={data} dataKey="revenue" nameKey="name" />;
  }
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="date" tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
        <YAxis tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
        <Tooltip contentStyle={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
        <Legend />
        <Line type="monotone" dataKey="loyalty" stroke="#6366f1" name="Loyalty" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="walkIn" stroke="#f59e0b" name="Walk-in" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
