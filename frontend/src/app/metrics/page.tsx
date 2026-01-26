"use client";

import { useEffect, useState, useCallback } from "react";
import { HeartRateChartWrapper } from "@/components/HeartRateChartWrapper";
import { EDAChartWrapper } from "@/components/EDAChartWrapper";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

interface HRDataPoint {
  datetime_utc: string;
  hr_mean: number;
  hr_std: number;
  hr_min: number;
  hr_max: number;
  sample_count: number;
}

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

interface MetricsData {
  date: string | null;
  hr: HRDataPoint[];
  eda: EDADataPoint[];
  tags: TagPoint[];
}

export default function MetricsPage() {
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [metricsData, setMetricsData] = useState<MetricsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch available dates on mount
  useEffect(() => {
    async function fetchDates() {
      try {
        const res = await fetch("/api/metrics/dates");
        if (!res.ok) throw new Error("Failed to fetch dates");
        const data = await res.json();
        setAvailableDates(data.dates || []);
      } catch (err) {
        console.error("Error fetching dates:", err);
        setError("Failed to load available dates");
      }
    }
    fetchDates();
  }, []);

  // Fetch metrics when date changes
  const fetchMetrics = useCallback(async (date?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const url = date ? `/api/metrics?date=${date}` : "/api/metrics";
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to fetch metrics");
      const data = await res.json();
      setMetricsData(data);
      if (data.date && !date) {
        setSelectedDate(data.date);
      }
    } catch (err) {
      console.error("Error fetching metrics:", err);
      setError("Failed to load metrics");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  const formatDisplayDate = (dateStr: string) => {
    const date = new Date(dateStr + "T00:00:00");
    return date.toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <main className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/">
              <ArrowLeft className="w-5 h-5" />
            </Link>
          </Button>
          <h1 className="text-2xl font-bold">Metrics</h1>
        </div>

        {/* Date Selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Date:</span>
          {availableDates.length === 0 ? (
            <span className="text-sm text-muted-foreground">No data available</span>
          ) : (
            <Select
              value={selectedDate}
              onValueChange={(value) => {
                setSelectedDate(value);
                fetchMetrics(value);
              }}
              disabled={isLoading}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Select date" />
              </SelectTrigger>
              <SelectContent>
                {availableDates.map((date) => (
                  <SelectItem key={date} value={date}>
                    {formatDisplayDate(date)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-600">
          {error}
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="grid gap-8">
          <Skeleton className="h-80 w-full rounded-xl" />
          <Skeleton className="h-80 w-full rounded-xl" />
        </div>
      )}

      {/* Charts */}
      {!isLoading && (
        <div className="grid gap-8">
          <HeartRateChartWrapper
            data={metricsData?.hr || []}
            tags={metricsData?.tags || []}
            isLoading={isLoading}
          />

          <EDAChartWrapper
            data={metricsData?.eda || []}
            tags={metricsData?.tags || []}
            isLoading={isLoading}
          />
        </div>
      )}

      {/* Summary Stats */}
      {metricsData && !isLoading && (
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div className="p-4 bg-muted/50 rounded-lg">
            <p className="text-muted-foreground">HR Data Points</p>
            <p className="text-2xl font-medium">{metricsData.hr.length}</p>
          </div>
          <div className="p-4 bg-muted/50 rounded-lg">
            <p className="text-muted-foreground">EDA Data Points</p>
            <p className="text-2xl font-medium">{metricsData.eda.length}</p>
          </div>
          <div className="p-4 bg-muted/50 rounded-lg">
            <p className="text-muted-foreground">Tags</p>
            <p className="text-2xl font-medium">{metricsData.tags.length}</p>
          </div>
        </div>
      )}
    </main>
  );
}
