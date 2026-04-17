"use client";

import { RevenueLineChart, DonutChart } from "@/components/charts/Charts";

interface Props {
  type: "line" | "donut";
  data: Record<string, unknown>[];
}

export default function OverviewCharts({ type, data }: Props) {
  if (type === "line") {
    return <RevenueLineChart data={data} lines={[]} />;
  }
  return <DonutChart data={data} dataKey="value" nameKey="name" />;
}
