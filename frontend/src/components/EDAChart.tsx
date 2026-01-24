"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  ReferenceLine,
  Tooltip,
} from "recharts";
import { Activity } from "lucide-react";

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

interface EDAChartProps {
  data: EDADataPoint[];
  tags?: TagPoint[];
  isLoading?: boolean;
}

const formatTime = (datetime: string) => {
  const date = new Date(datetime);
  const hours = date.getHours().toString().padStart(2, "0");
  const minutes = date.getMinutes().toString().padStart(2, "0");
  return `${hours}:${minutes}`;
};

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; payload: EDADataPoint }>;
}

const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    const dataPoint = payload[0].payload;
    return (
      <div className="bg-card border border-border rounded-lg px-3 py-2 shadow-lg">
        <p className="text-xs text-muted-foreground mb-1">
          {formatTime(dataPoint.datetime_utc)}
        </p>
        <p className="text-foreground font-medium">
          {payload[0].value.toFixed(2)} µS
        </p>
        <p className="text-xs text-muted-foreground">
          Range: {dataPoint.eda_min.toFixed(2)}-{dataPoint.eda_max.toFixed(2)}
        </p>
      </div>
    );
  }
  return null;
};

export const EDAChart = ({
  data,
  tags = [],
  isLoading,
}: EDAChartProps) => {
  const validData = useMemo(() => {
    return data.filter(
      (d) => typeof d.eda_mean === "number" && d.eda_mean !== null
    );
  }, [data]);

  const displayAvgEDA = useMemo(() => {
    if (validData.length === 0) return 0;
    return (
      validData.reduce((sum, d) => sum + d.eda_mean, 0) / validData.length
    ).toFixed(2);
  }, [validData]);

  // Create a set of tag times for quick lookup
  const tagTimes = useMemo(() => {
    return new Set(tags.map((t) => formatTime(t.datetime_utc)));
  }, [tags]);

  // Find data points that match tag times
  const taggedDataPoints = useMemo(() => {
    return validData.filter((d) => tagTimes.has(formatTime(d.datetime_utc)));
  }, [validData, tagTimes]);

  // Calculate Y-axis domain dynamically
  const yDomain = useMemo(() => {
    if (validData.length === 0) return [0, 25];
    const values = validData.map((d) => d.eda_mean);
    const min = Math.max(0, Math.floor(Math.min(...values) - 1));
    const max = Math.ceil(Math.max(...values) + 1);
    return [min, max];
  }, [validData]);

  if (isLoading) {
    return (
      <div className="metric-card">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-5 h-5 text-primary" />
          <h3 className="font-medium text-foreground">Electrodermal Activity</h3>
        </div>
        <div className="h-48 flex items-center justify-center">
          <div className="animate-pulse text-muted-foreground">Loading...</div>
        </div>
      </div>
    );
  }

  if (validData.length === 0) {
    return (
      <div className="metric-card">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-5 h-5 text-primary" />
          <h3 className="font-medium text-foreground">Electrodermal Activity</h3>
        </div>
        <div className="h-48 flex items-center justify-center">
          <p className="text-muted-foreground">No EDA data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="metric-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          <h3 className="font-medium text-foreground">Electrodermal Activity</h3>
          {tags.length > 0 && (
            <span className="text-xs bg-red-500/20 text-red-600 px-2 py-0.5 rounded-full">
              {tags.length} tag{tags.length > 1 ? "s" : ""}
            </span>
          )}
        </div>
        <span className="text-sm text-muted-foreground">
          {validData.length} data points
        </span>
      </div>

      <div className="mb-6">
        <span className="text-4xl font-serif font-medium text-foreground">
          {displayAvgEDA}
        </span>
        <span className="text-muted-foreground ml-2">avg µS</span>
      </div>

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={validData}
            margin={{ top: 10, right: 10, left: 0, bottom: 20 }}
          >
            <XAxis
              dataKey="datetime_utc"
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
              axisLine={{ stroke: "hsl(var(--border))" }}
              tickLine={false}
              tickFormatter={formatTime}
              interval={Math.floor(validData.length / 5)}
            />
            <YAxis
              domain={yDomain}
              tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => v.toFixed(1)}
            />
            <Tooltip
              content={<CustomTooltip />}
              cursor={{ stroke: "hsl(var(--border))", strokeWidth: 1 }}
            />
            {taggedDataPoints.map((tag, idx) => (
              <ReferenceLine
                key={idx}
                x={tag.datetime_utc}
                stroke="#ef4444"
                strokeWidth={2}
                label={{
                  value: "●",
                  position: "top",
                  fill: "#ef4444",
                  fontSize: 10,
                }}
              />
            ))}
            <Line
              type="monotone"
              dataKey="eda_mean"
              stroke="#8b5cf6"
              strokeWidth={2}
              dot={false}
              activeDot={{
                r: 6,
                fill: "#8b5cf6",
                stroke: "hsl(var(--background))",
                strokeWidth: 2,
              }}
              animationDuration={1500}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="h-3 bg-violet-500/30 rounded-full mt-4" />
    </div>
  );
};
