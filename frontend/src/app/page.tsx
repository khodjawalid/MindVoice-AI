"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { BarChart3, Activity, Heart, ChevronRight } from "lucide-react";

interface TableResult {
  status: string;
  rows_uploaded?: number;
  reason?: string;
}

interface DateResult {
  status: string;
  reason?: string;
  date?: string;
  eda_aggregated?: TableResult;
  hr_aggregated?: TableResult;
  tags?: TableResult;
}

interface SyncResult {
  status: string;
  date?: string;
  migration?: {
    status: string;
    migrated_count?: number;
    skipped_count?: number;
    results?: Record<string, DateResult>;
  };
}

export default function Home() {
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await fetch("/api/sync", { method: "POST" });
      const data = await res.json();
      setSyncResult(data);
    } catch {
      setSyncResult({ status: "error" });
    }
    setSyncing(false);
  };

  return (
    <main className="p-8 max-w-4xl mx-auto space-y-8">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">MindVoice</h1>
        <p className="text-muted-foreground">Your personal wellness companion</p>
      </div>

      <nav className="grid gap-3">
        <Link
          href="/dashboard"
          className="flex items-center justify-between p-4 bg-card border border-border rounded-xl hover:border-primary/50 hover:shadow-soft transition-all group"
        >
          <div className="flex items-center gap-3">
            <BarChart3 className="w-5 h-5 text-sage" />
            <span className="font-medium">Stress Dashboard</span>
          </div>
          <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-foreground transition-colors" />
        </Link>
        <Link
          href="/metrics"
          className="flex items-center justify-between p-4 bg-card border border-border rounded-xl hover:border-primary/50 hover:shadow-soft transition-all group"
        >
          <div className="flex items-center gap-3">
            <Activity className="w-5 h-5 text-sage" />
            <span className="font-medium">View Metrics</span>
          </div>
          <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-foreground transition-colors" />
        </Link>
        <Link
          href="/wellness"
          className="flex items-center justify-between p-4 bg-card border border-border rounded-xl hover:border-primary/50 hover:shadow-soft transition-all group"
        >
          <div className="flex items-center gap-3">
            <Heart className="w-5 h-5 text-sage" />
            <span className="font-medium">Wellness Session</span>
          </div>
          <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-foreground transition-colors" />
        </Link>
      </nav>

      <section className="space-y-3">
        <Button
          onClick={handleSync}
          disabled={syncing}
          variant="sync"
          size="lg"
        >
          {syncing ? "Syncing..." : "Sync Empatica"}
        </Button>
        {syncResult && (
          <div className="text-sm space-y-1">
            <p className={syncResult.status === "error" ? "text-red-600" : "text-green-600"}>
              Sync: {syncResult.status} {syncResult.date && `(${syncResult.date})`}
            </p>
            {syncResult.migration && (
              <div className="pl-4 text-gray-600">
                <p>
                  Migration: {syncResult.migration.status}
                  {syncResult.migration.migrated_count !== undefined && (
                    <span className="ml-2">
                      ({syncResult.migration.migrated_count} migrated, {syncResult.migration.skipped_count} skipped)
                    </span>
                  )}
                </p>
                {syncResult.migration.results && (
                  <ul className="pl-4 text-xs space-y-1">
                    {Object.entries(syncResult.migration.results).map(([date, result]) => (
                      <li key={date}>
                        {date}:{" "}
                        {result.status === "skipped" ? (
                          <span className="text-gray-500">skipped (already exists)</span>
                        ) : (
                          <span className="text-green-600">
                            migrated ({result.eda_aggregated?.rows_uploaded ?? 0} EDA,{" "}
                            {result.hr_aggregated?.rows_uploaded ?? 0} HR,{" "}
                            {result.tags?.rows_uploaded ?? 0} tags)
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
