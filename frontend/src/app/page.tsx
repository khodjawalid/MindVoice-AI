"use client";

import Link from "next/link";
import { useState } from "react";

export default function Home() {
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    setSyncStatus(null);
    try {
      const res = await fetch("/api/sync", { method: "POST" });
      const data = await res.json();
      setSyncStatus(data.status);
    } catch {
      setSyncStatus("error");
    }
    setSyncing(false);
  };

  return (
    <main className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">MindVoice</h1>
      <nav className="space-y-2">
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
        {syncStatus && (
          <p className={`text-sm ${syncStatus === "error" ? "text-red-600" : "text-green-600"}`}>
            Status: {syncStatus}
          </p>
        )}
      </section>
    </main>
  );
}
