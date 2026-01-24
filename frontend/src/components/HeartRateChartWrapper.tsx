"use client";

import dynamic from "next/dynamic";

const HeartRateChart = dynamic(
  () => import("@/components/HeartRateChart").then((mod) => mod.HeartRateChart),
  { ssr: false, loading: () => <div className="metric-card h-80 animate-pulse" /> }
);

interface HRDataPoint {
  datetime_utc: string;
  hr_mean: number;
  hr_std: number;
  hr_min: number;
  hr_max: number;
  sample_count: number;
}

interface TagPoint {
  datetime_utc: string;
  timestamp: number;
}

interface HeartRateChartWrapperProps {
  data: HRDataPoint[];
  tags?: TagPoint[];
  isLoading?: boolean;
}

export const HeartRateChartWrapper = (props: HeartRateChartWrapperProps) => {
  return <HeartRateChart {...props} />;
};
