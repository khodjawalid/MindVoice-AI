"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import StressScoreChart from "@/components/StressScoreChart";
import { ArrowLeft, RefreshCw, Calendar, Tag } from "lucide-react";

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
  const router = useRouter();
  const date = params.date as string;

  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [inferring, setInferring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/dashboard?date=${date}`);
      if (!res.ok) {
        throw new Error("Failed to fetch dashboard data");
      }
      const result = await res.json();
      setData(result);
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
          <Link
            href="/dashboard"
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
            <p className="text-muted-foreground flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              {formatDate(date)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => runInference(true)}
            disabled={inferring}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw
              className={`w-4 h-4 ${inferring ? "animate-spin" : ""}`}
            />
            {inferring ? "Running..." : "Re-run Inference"}
          </button>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 text-destructive">
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">Loading dashboard data...</div>
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
              <button
                onClick={() => runInference(false)}
                disabled={inferring}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
              >
                Run Inference
              </button>
            </div>
          )}
        </>
      )}
    </main>
  );
}
