"use client";

import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

const COLORS = ["#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];

interface ChartProps {
  data: Record<string, unknown>[];
  height?: number;
}

export function RevenueLineChart({ data, height = 300 }: ChartProps & { lines: { key: string; color: string }[] }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="date" tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
        <YAxis tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
        <Tooltip contentStyle={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
        <Legend />
        <Line type="monotone" dataKey="franchiseA" stroke="#6366f1" name="Franchise A" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="franchiseB" stroke="#f59e0b" name="Franchise B" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function SimpleBarChart({ data, dataKey, nameKey, height = 300 }: ChartProps & { dataKey: string; nameKey: string }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 80 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis type="number" tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
        <YAxis type="category" dataKey={nameKey} tick={{ fontSize: 12, fill: "var(--text-secondary)" }} width={80} />
        <Tooltip contentStyle={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
        <Bar dataKey={dataKey} fill="#6366f1" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function VerticalBarChart({ data, bars, nameKey, height = 300 }: ChartProps & { bars: { key: string; color: string }[]; nameKey: string }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey={nameKey} tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
        <YAxis tick={{ fontSize: 12, fill: "var(--text-secondary)" }} />
        <Tooltip contentStyle={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
        <Legend />
        {bars.map(({ key, color }) => (
          <Bar key={key} dataKey={key} fill={color} radius={[4, 4, 0, 0]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function DonutChart({ data, dataKey, nameKey, height = 300 }: ChartProps & { dataKey: string; nameKey: string }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={data} dataKey={dataKey} nameKey={nameKey} cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={2} label>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)" }} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
