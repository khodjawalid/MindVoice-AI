"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { DashboardCard } from "@/components/dashboard/DashboardCard";
import { Heart, Activity, Calendar } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";

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
    <div className="min-h-screen bg-background">
      <Header variant="dashboard" userName="Matthieu" />

      <main className="pt-24 pb-12 px-6">
        <div className="container mx-auto max-w-4xl">
          <motion.h1
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="font-serif text-2xl font-semibold text-foreground mb-8"
          >
            Hello Matthieu
          </motion.h1>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            <DashboardCard
              title="Wellness"
              icon={Heart}
              href="/wellness"
              delay={0.1}
            />
            <DashboardCard
              title="Key Metrics"
              icon={Activity}
              href="/dashboard"
              delay={0.2}
            />
            <DashboardCard
              title="Dashboard"
              icon={Calendar}
              href="/metrics"
              delay={0.3}
            />
          </div>

          <motion.section
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="space-y-3"
          >
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
                  <div className="pl-4 text-muted-foreground">
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
                              <span className="text-muted-foreground">skipped (already exists)</span>
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
          </motion.section>
        </div>
      </main>
    </div>
  );
}
