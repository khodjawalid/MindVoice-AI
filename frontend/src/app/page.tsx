"use client";

import Link from "next/link";
import { useState } from "react";

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
    <main className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">MindVoice</h1>
      <nav className="space-y-2">
        <Link href="/dashboard" className="block text-blue-600 hover:underline">
          Stress Dashboard &rarr;
        </Link>
        <Link href="/metrics" className="block text-blue-600 hover:underline">
          View Metrics &rarr;
        </Link>
        <Link href="/wellness" className="block text-blue-600 hover:underline">
          Wellness Session &rarr;
        </Link>
      </nav>

      <section className="space-y-2">
        <button
          onClick={handleSync}
          disabled={syncing}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {syncing ? "Syncing..." : "Sync Empatica"}
        </button>
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
