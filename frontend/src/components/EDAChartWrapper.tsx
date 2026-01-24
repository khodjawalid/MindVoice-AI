"use client";

import dynamic from "next/dynamic";

const EDAChart = dynamic(
  () => import("@/components/EDAChart").then((mod) => mod.EDAChart),
  { ssr: false, loading: () => <div className="metric-card h-80 animate-pulse" /> }
);

interface EDADataPoint {
  datetime_utc: string;
  eda_mean: number;
  eda_std: number;
  eda_min: number;
  eda_max: number;
  sample_count: number;
}

interface TagPoint {
  datetime_utc: string;
  timestamp: number;
}

interface EDAChartWrapperProps {
  data: EDADataPoint[];
  tags?: TagPoint[];
  isLoading?: boolean;
}

export const EDAChartWrapper = (props: EDAChartWrapperProps) => {
  return <EDAChart {...props} />;
};
