"use client";

import { SimpleBarChart, VerticalBarChart } from "@/components/charts/Charts";

interface Props {
  type: "bar" | "stacked" | "brandBar";
  data: Record<string, unknown>[];
}

export default function CategoriesCharts({ type, data }: Props) {
  if (type === "bar") {
    return <SimpleBarChart data={data} dataKey="revenue" nameKey="category" />;
  }
  if (type === "stacked") {
    return (
      <VerticalBarChart
        data={data}
        bars={[
          { key: "franchiseA", color: "#6366f1" },
          { key: "franchiseB", color: "#f59e0b" },
        ]}
        nameKey="category"
      />
    );
  }
  return <SimpleBarChart data={data} dataKey="revenue" nameKey="brand" />;
}
