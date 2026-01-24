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
import { Heart } from "lucide-react";

interface DataPoint {
  timestamp_unix: number;
  timestamp_iso: string;
  heart_rate: number | null;
  eda: number | null;
  has_tag: boolean;
}

interface HeartRateChartProps {
  data: DataPoint[];
  avgHR?: number;
  isLoading?: boolean;
}

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp);
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
};

const formatTimeWithSeconds = (timestamp: number) => {
  const date = new Date(timestamp);
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  const seconds = date.getSeconds().toString().padStart(2, '0');
  return `${hours}:${minutes}:${seconds}`;
};

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; payload: DataPoint }>;
}

const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
  if (active && payload && payload.length) {
    const dataPoint = payload[0].payload;
    return (
      <div className="bg-card border border-border rounded-lg px-3 py-2 shadow-lg">
        <p className="text-xs text-muted-foreground mb-1">{formatTimeWithSeconds(dataPoint.timestamp_unix)}</p>
        <p className="text-foreground font-medium">{Math.round(payload[0].value)} bpm</p>
      </div>
    );
  }
  return null;
};

export const HeartRateChart = ({ data, avgHR, isLoading }: HeartRateChartProps) => {
  const validData = useMemo(() => {
    return data.filter(d => typeof d.heart_rate === 'number' && d.heart_rate !== null);
  }, [data]);

  const taggedPoints = useMemo(() => {
    return data.filter(d => d.has_tag);
  }, [data]);

  const displayAvgHR = useMemo(() => {
    if (avgHR !== undefined) return avgHR;
    if (validData.length === 0) return 0;
    return Math.round(validData.reduce((sum, d) => sum + (d.heart_rate as number), 0) / validData.length);
  }, [avgHR, validData]);

  const dateLabel = useMemo(() => {
    if (data.length === 0) return '';
    const date = new Date(data[0].timestamp_unix);
    return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  }, [data]);

  if (isLoading) {
    return (
      <div className="metric-card">
        <div className="flex items-center gap-2 mb-4">
          <Heart className="w-5 h-5 text-primary" />
          <h3 className="font-medium text-foreground">Heart Rate</h3>
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
          <Heart className="w-5 h-5 text-primary" />
          <h3 className="font-medium text-foreground">Heart Rate</h3>
        </div>
        <div className="h-48 flex items-center justify-center">
          <p className="text-muted-foreground">No heart rate data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="metric-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Heart className="w-5 h-5 text-primary" />
          <h3 className="font-medium text-foreground">Heart Rate</h3>
          {taggedPoints.length > 0 && (
            <span className="text-xs bg-red-500/20 text-red-600 px-2 py-0.5 rounded-full">
              {taggedPoints.length} tag{taggedPoints.length > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <span className="text-sm text-muted-foreground">{dateLabel}</span>
      </div>

      <div className="mb-6">
        <span className="text-4xl font-serif font-medium text-foreground">{displayAvgHR}</span>
        <span className="text-muted-foreground ml-2">avg bpm</span>
      </div>

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={validData} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
            <XAxis
              dataKey="timestamp_unix"
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              axisLine={{ stroke: 'hsl(var(--border))' }}
              tickLine={false}
              tickFormatter={formatTime}
              interval={Math.floor(validData.length / 5)}
            />
            <YAxis domain={[40, 140]} ticks={[45, 80, 140]} tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'hsl(var(--border))', strokeWidth: 1 }} />
            <ReferenceLine y={80} stroke="hsl(var(--border))" strokeDasharray="4 4" />
            {taggedPoints.map((tag, idx) => (
              <ReferenceLine
                key={idx}
                x={tag.timestamp_unix}
                stroke="#ef4444"
                strokeWidth={2}
                label={{ value: '●', position: 'top', fill: '#ef4444', fontSize: 10 }}
              />
            ))}
            <Line
              type="monotone"
              dataKey="heart_rate"
              stroke="var(--sage)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6, fill: 'var(--sage)', stroke: 'hsl(var(--background))', strokeWidth: 2 }}
              animationDuration={1500}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="h-3 bg-olive rounded-full mt-4" />
    </div>
  );
};
