"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import StressScoreChart from "@/components/StressScoreChart";
import { VideoInferenceChart } from "@/components/VideoInferenceChart";
import { ArrowLeft, RefreshCw, Calendar, Tag } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

interface StressScore {
  id: string;
  datetime_utc: string;
  stress_proba: number;
  stress_pred: number;
  eda_coverage: number;
  hr_coverage: number;
}

interface TagData {
  id: string;
  datetime_utc: string;
  timestamp: number;
  emotion_label?: string;
  stress_level?: number;
  reviewed?: boolean;
}

interface DailyInference {
  id: string;
  record_date: string;
  predicted_emotion: string;
  pred_confidence: number;
  emotion_probabilities: Record<string, number>;
  created_at?: string;
}

interface DashboardData {
  date: string;
  scores: StressScore[];
  tags: TagData[];
  reviewed_tags: TagData[];
  summary: {
    avg_stress_proba?: number;
    stress_ratio?: number;
    total_windows?: number;
    valid_windows?: number;
  };
  has_data: boolean;
}

export default function DashboardDatePage() {
  const params = useParams();
  const date = params.date as string;

  const [data, setData] = useState<DashboardData | null>(null);
  const [dailyInference, setDailyInference] = useState<DailyInference | null>(null);
  const [loading, setLoading] = useState(true);
  const [inferring, setInferring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch both dashboard data and daily inference in parallel
      const [dashboardRes, dailyRes] = await Promise.all([
        fetch(`/api/dashboard?date=${date}`),
        fetch(`/api/dashboard/daily-inference?date=${date}`),
      ]);

      if (!dashboardRes.ok) {
        throw new Error("Failed to fetch dashboard data");
      }
      const dashboardResult = await dashboardRes.json();
      setData(dashboardResult);

      if (dailyRes.ok) {
        const dailyResult = await dailyRes.json();
        setDailyInference(dailyResult.data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
    setLoading(false);
  }, [date]);

  const runInference = async (force = false) => {
    setInferring(true);
    try {
      const res = await fetch("/api/dashboard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date, force }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Inference failed");
      }
      // Refresh data after inference
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
    setInferring(false);
  };

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("fr-FR", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  return (
    <main className="p-8 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/dashboard">
              <ArrowLeft className="w-5 h-5" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
            <p className="text-muted-foreground flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              {formatDate(date)}
            </p>
          </div>
        </div>

        <Button
          onClick={() => runInference(true)}
          disabled={inferring}
          variant="default"
        >
          <RefreshCw
            className={`w-4 h-4 ${inferring ? "animate-spin" : ""}`}
          />
          {inferring ? "Running..." : "Re-run Inference"}
        </Button>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 text-destructive">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
            <Skeleton className="h-24 rounded-xl" />
          </div>
          <Skeleton className="h-64 rounded-xl" />
        </div>
      )}

      {/* Data Display */}
      {!loading && data && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-card border border-border rounded-xl p-4">
              <p className="text-sm text-muted-foreground">Avg Stress</p>
              <p className="text-2xl font-bold text-foreground">
                {data.summary.avg_stress_proba !== undefined
                  ? `${(data.summary.avg_stress_proba * 100).toFixed(1)}%`
                  : "N/A"}
              </p>
            </div>
            <div className="bg-card border border-border rounded-xl p-4">
              <p className="text-sm text-muted-foreground">Stress Ratio</p>
              <p
                className={`text-2xl font-bold ${
                  data.summary.stress_ratio !== undefined &&
                  data.summary.stress_ratio > 0.5
                    ? "text-red-500"
                    : "text-green-500"
                }`}
              >
                {data.summary.stress_ratio !== undefined
                  ? `${(data.summary.stress_ratio * 100).toFixed(0)}%`
                  : "N/A"}
              </p>
            </div>
            <div className="bg-card border border-border rounded-xl p-4">
              <p className="text-sm text-muted-foreground">Data Points</p>
              <p className="text-2xl font-bold text-foreground">
                {data.summary.valid_windows ?? 0} / {data.summary.total_windows ?? 0}
              </p>
            </div>
            <div className="bg-card border border-border rounded-xl p-4">
              <p className="text-sm text-muted-foreground">Reviewed Tags</p>
              <p className="text-2xl font-bold text-foreground">
                {data.reviewed_tags?.length ?? 0}
              </p>
            </div>
          </div>

          {/* Stress Score Chart */}
          <StressScoreChart
            data={data.scores}
            tags={data.tags}
            isLoading={loading}
          />

          {/* Daily Video Emotion Analysis Chart */}
          <VideoInferenceChart
            dailyInference={dailyInference}
            date={date}
          />

          {/* Reviewed Tags Section */}
          {data.reviewed_tags && data.reviewed_tags.length > 0 && (
            <div className="bg-card border border-border rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Tag className="w-5 h-5 text-primary" />
                <h3 className="font-medium text-foreground">
                  Reviewed Tags ({data.reviewed_tags.length})
                </h3>
              </div>
              <div className="space-y-3">
                {data.reviewed_tags.map((tag) => {
                  const time = new Date(tag.datetime_utc).toLocaleTimeString(
                    "fr-FR",
                    { hour: "2-digit", minute: "2-digit" }
                  );
                  return (
                    <div
                      key={tag.id}
                      className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                    >
                      <div className="flex items-center gap-4">
                        <span className="text-sm font-mono text-muted-foreground">
                          {time}
                        </span>
                        {tag.emotion_label && (
                          <span className="px-2 py-1 bg-blue-500/10 text-blue-500 rounded text-sm">
                            {tag.emotion_label}
                          </span>
                        )}
                      </div>
                      {tag.stress_level !== undefined && (
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-muted-foreground">
                            Stress Level:
                          </span>
                          <span
                            className={`font-bold ${
                              tag.stress_level > 5
                                ? "text-red-500"
                                : tag.stress_level > 3
                                ? "text-yellow-500"
                                : "text-green-500"
                            }`}
                          >
                            {tag.stress_level}/10
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* No Data State */}
          {!data.has_data && (
            <div className="bg-muted/50 border border-border rounded-xl p-8 text-center">
              <p className="text-muted-foreground mb-4">
                No inference data available for this date.
              </p>
              <Button
                onClick={() => runInference(false)}
                disabled={inferring}
                variant="sage"
              >
                Run Inference
              </Button>
            </div>
          )}
        </>
      )}
    </main>
  );
}
