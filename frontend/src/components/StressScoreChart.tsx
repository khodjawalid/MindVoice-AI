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
  Area,
  AreaChart,
} from "recharts";
import { Activity } from "lucide-react";

interface StressScorePoint {
  datetime_utc: string;
  stress_proba: number;
  stress_pred: number;
  eda_coverage: number;
  hr_coverage: number;
}

interface TagPoint {
  datetime_utc: string;
  timestamp: number;
  emotion_label?: string;
  stress_level?: number;
  reviewed?: boolean;
}

interface StressScoreChartProps {
  data: StressScorePoint[];
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
  payload?: Array<{ value: number; payload: StressScorePoint }>;
}

const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    const dataPoint = payload[0].payload;
    const isStressed = dataPoint.stress_pred === 1;
    return (
      <div className="bg-card border border-border rounded-lg px-3 py-2 shadow-lg">
        <p className="text-xs text-muted-foreground mb-1">
          {formatTime(dataPoint.datetime_utc)}
        </p>
        <p className="text-foreground font-medium">
          Stress: {(dataPoint.stress_proba * 100).toFixed(1)}%
        </p>
        <p
          className={`text-sm font-semibold ${
            isStressed ? "text-red-500" : "text-green-500"
          }`}
        >
          {isStressed ? "Stressed" : "Relaxed"}
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Coverage: EDA {(dataPoint.eda_coverage * 100).toFixed(0)}%, HR{" "}
          {(dataPoint.hr_coverage * 100).toFixed(0)}%
        </p>
      </div>
    );
  }
  return null;
};

export const StressScoreChart = ({
  data,
  tags = [],
  isLoading,
}: StressScoreChartProps) => {
  const validData = useMemo(() => {
    return data.filter(
      (d) => typeof d.stress_proba === "number" && d.stress_proba !== null
    );
  }, [data]);

  const displayAvgStress = useMemo(() => {
    if (validData.length === 0) return 0;
    return (
      (validData.reduce((sum, d) => sum + d.stress_proba, 0) /
        validData.length) *
      100
    ).toFixed(1);
  }, [validData]);

  const stressRatio = useMemo(() => {
    if (validData.length === 0) return 0;
    const stressedCount = validData.filter((d) => d.stress_pred === 1).length;
    return ((stressedCount / validData.length) * 100).toFixed(0);
  }, [validData]);

  // Create a set of reviewed tag times for quick lookup
  const tagTimes = useMemo(() => {
    return new Set(
      tags
        .filter((t) => t.reviewed)
        .map((t) => formatTime(t.datetime_utc))
    );
  }, [tags]);

  // Find data points that match tag times
  const taggedDataPoints = useMemo(() => {
    return validData.filter((d) => tagTimes.has(formatTime(d.datetime_utc)));
  }, [validData, tagTimes]);

  if (isLoading) {
    return (
      <div className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-5 h-5 text-primary" />
          <h3 className="font-medium text-foreground">Stress Score</h3>
        </div>
        <div className="h-64 flex items-center justify-center text-muted-foreground">
          Loading...
        </div>
      </div>
    );
  }

  if (validData.length === 0) {
    return (
      <div className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-5 h-5 text-primary" />
          <h3 className="font-medium text-foreground">Stress Score</h3>
        </div>
        <div className="h-64 flex items-center justify-center text-muted-foreground">
          No stress data available. Run inference to generate scores.
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          <h3 className="font-medium text-foreground">Stress Score</h3>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <div className="text-right">
            <span className="text-muted-foreground">Avg: </span>
            <span className="text-foreground font-medium">
              {displayAvgStress}%
            </span>
          </div>
          <div className="text-right">
            <span className="text-muted-foreground">Stressed: </span>
            <span
              className={`font-medium ${
                Number(stressRatio) > 50 ? "text-red-500" : "text-green-500"
              }`}
            >
              {stressRatio}%
            </span>
          </div>
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={validData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="stressGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="datetime_utc"
              tickFormatter={formatTime}
              stroke="hsl(var(--muted-foreground))"
              fontSize={10}
              tickLine={false}
              axisLine={false}
              interval={Math.max(0, Math.floor(validData.length / 20) - 1)}
              minTickGap={30}
            />
            <YAxis
              domain={[0, 1]}
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
              width={45}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Threshold line at 0.5 */}
            <ReferenceLine
              y={0.5}
              stroke="hsl(var(--muted-foreground))"
              strokeDasharray="3 3"
              opacity={0.5}
            />

            {/* Tag reference lines */}
            {tags
              .filter((t) => t.reviewed)
              .map((tag, i) => (
                <ReferenceLine
                  key={`tag-${i}`}
                  x={tag.datetime_utc}
                  stroke="#a855f7"
                  strokeDasharray="4 4"
                  opacity={0.7}
                />
              ))}

            <Area
              type="monotone"
              dataKey="stress_proba"
              stroke="#8b5cf6"
              strokeWidth={2}
              fill="url(#stressGradient)"
              dot={false}
              activeDot={{
                r: 4,
                fill: "#8b5cf6",
                stroke: "#fff",
                strokeWidth: 2,
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="mt-4 flex items-center gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full bg-violet-500" />
          <span>Stress Probability</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-0.5 bg-muted-foreground opacity-50" />
          <span>50% Threshold</span>
        </div>
        {tags.filter((t) => t.reviewed).length > 0 && (
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5 bg-purple-500" style={{ opacity: 0.7 }} />
            <span>Reviewed Tags</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default StressScoreChart;
