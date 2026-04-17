"use client";

import { SimpleBarChart, DonutChart } from "@/components/charts/Charts";

interface Props {
  type: "bar" | "donut";
  data: Record<string, unknown>[];
}

export default function TrendsCharts({ type, data }: Props) {
  if (type === "bar") {
    return <SimpleBarChart data={data} dataKey="units" nameKey="name" />;
  }
  return <DonutChart data={data} dataKey="value" nameKey="name" height={350} />;
}
