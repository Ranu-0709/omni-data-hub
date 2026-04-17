"use client";

import { SimpleBarChart } from "@/components/charts/Charts";

interface Props {
  data: Record<string, unknown>[];
}

export default function LocationsCharts({ data }: Props) {
  return <SimpleBarChart data={data} dataKey="revenue" nameKey="name" />;
}
