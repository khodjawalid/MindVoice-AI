"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Calendar, ChevronRight, BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

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
    <main className="min-h-screen bg-background">
      <div className="p-8 max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild className="rounded-full hover:bg-sage-light">
            <Link href="/home">
              <ArrowLeft className="w-5 h-5" />
            </Link>
          </Button>
          <div>
            <h1 className="font-serif text-2xl md:text-3xl font-medium text-foreground flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-sage-light flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-sage" />
              </div>
              Stress Dashboard
            </h1>
            <p className="text-muted-foreground mt-1">
              Visualize inferred stress scores by date
            </p>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full rounded-2xl" />
            <Skeleton className="h-20 w-full rounded-2xl" />
            <Skeleton className="h-20 w-full rounded-2xl" />
          </div>
        )}

        {/* Empty State */}
        {!loading && dates.length === 0 && (
          <div className="bg-sage-light/50 border border-sage/20 rounded-2xl p-8 text-center">
            <div className="w-16 h-16 rounded-2xl bg-sage-light flex items-center justify-center mx-auto mb-4">
              <Calendar className="w-8 h-8 text-sage" />
            </div>
            <p className="text-muted-foreground mb-4">
              No data available. Sync Empatica data to get started.
            </p>
            <Button className="rounded-full px-6 bg-sage hover:bg-sage-dark text-white" asChild>
              <Link href="/home">Go to Home</Link>
            </Button>
          </div>
        )}

        {/* Date List */}
        {!loading && dates.length > 0 && (
          <div className="space-y-3">
            {dates.map((date) => (
              <Link
                key={date}
                href={`/dashboard/${date}`}
                className="flex items-center justify-between p-5 bg-card border border-border rounded-2xl hover:border-sage hover:shadow-card transition-all group"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-sage-light flex items-center justify-center group-hover:bg-sage transition-colors">
                    <Calendar className="w-5 h-5 text-sage group-hover:text-white transition-colors" />
                  </div>
                  <div>
                    <p className="font-serif font-medium text-foreground">{formatDate(date)}</p>
                    <p className="text-sm text-muted-foreground">{date}</p>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-sage transition-colors" />
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
