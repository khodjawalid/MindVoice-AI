"use client";

import dynamic from "next/dynamic";

const HeartRateChart = dynamic(
  () => import("@/components/HeartRateChart").then(mod => mod.HeartRateChart),
  { ssr: false, loading: () => <div className="metric-card h-80 animate-pulse" /> }
);

interface DataPoint {
  timestamp_unix: number;
  timestamp_iso: string;
  heart_rate: number | null;
  eda: number | null;
  has_tag: boolean;
}

interface HeartRateChartWrapperProps {
  data: DataPoint[];
  avgHR?: number;
  isLoading?: boolean;
}

export const HeartRateChartWrapper = (props: HeartRateChartWrapperProps) => {
  return <HeartRateChart {...props} />;
};
