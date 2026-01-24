"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Calendar, ChevronRight, BarChart3 } from "lucide-react";

interface DateSummary {
  date: string;
}

export default function DashboardPage() {
  const [dates, setDates] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDates = async () => {
      try {
        const res = await fetch("/api/dashboard");
        if (res.ok) {
          const data = await res.json();
          setDates(data.dates || []);
        }
      } catch (error) {
        console.error("Failed to fetch dates:", error);
      }
      setLoading(false);
    };

    fetchDates();
  }, []);

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
    <main className="p-8 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/"
          className="p-2 rounded-lg hover:bg-muted transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-primary" />
            Stress Dashboard
          </h1>
          <p className="text-muted-foreground">
            Visualize inferred stress scores by date
          </p>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground">Loading available dates...</div>
        </div>
      )}

      {/* Empty State */}
      {!loading && dates.length === 0 && (
        <div className="bg-muted/50 border border-border rounded-xl p-8 text-center">
          <Calendar className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <p className="text-muted-foreground">
            No data available. Sync Empatica data to get started.
          </p>
          <Link
            href="/"
            className="inline-block mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
          >
            Go to Home
          </Link>
        </div>
      )}

      {/* Date List */}
      {!loading && dates.length > 0 && (
        <div className="space-y-2">
          {dates.map((date) => (
            <Link
              key={date}
              href={`/dashboard/${date}`}
              className="flex items-center justify-between p-4 bg-card border border-border rounded-xl hover:border-primary/50 hover:bg-muted/50 transition-all group"
            >
              <div className="flex items-center gap-3">
                <Calendar className="w-5 h-5 text-muted-foreground group-hover:text-primary transition-colors" />
                <div>
                  <p className="font-medium text-foreground">{formatDate(date)}</p>
                  <p className="text-sm text-muted-foreground">{date}</p>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-foreground transition-colors" />
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
