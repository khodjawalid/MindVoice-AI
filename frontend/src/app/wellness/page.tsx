"use client";

import { useEffect, useState, useCallback } from "react";
import { TagReviewList } from "@/components/TagReviewList";
import Link from "next/link";

interface TagReview {
  id: string;
  record_date: string;
  timestamp: number;
  datetime_utc: string;
  emotion_label: string | null;
  stress_level: number | null;
  video_url: string | null;
  reviewed: boolean;
  created_at: string;
}

interface TagsData {
  date: string | null;
  data: TagReview[];
  count: number;
}

export default function WellnessPage() {
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [tagsData, setTagsData] = useState<TagsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch available dates on mount
  useEffect(() => {
    async function fetchDates() {
      try {
        const res = await fetch("/api/wellness/dates");
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

  // Fetch tags when date changes
  const fetchTags = useCallback(async (date?: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const url = date ? `/api/wellness?date=${date}` : "/api/wellness";
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to fetch tags");
      const data = await res.json();
      setTagsData(data);
      if (data.date && !date) {
        setSelectedDate(data.date);
      }
    } catch (err) {
      console.error("Error fetching tags:", err);
      setError("Failed to load tags");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  // Handle date selection change
  const handleDateChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const date = e.target.value;
    setSelectedDate(date);
    fetchTags(date);
  };

  // Refresh data after update
  const handleTagUpdate = () => {
    if (selectedDate) {
      fetchTags(selectedDate);
    }
  };

  const formatDisplayDate = (dateStr: string) => {
    const date = new Date(dateStr + "T00:00:00");
    return date.toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const pendingCount = tagsData?.data.filter((t) => !t.reviewed).length || 0;
  const reviewedCount = tagsData?.data.filter((t) => t.reviewed).length || 0;

  return (
    <main className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-muted-foreground hover:text-foreground">
            &larr; Back
          </Link>
          <h1 className="text-2xl font-bold">Wellness Tags</h1>
        </div>

        {/* Date Selector */}
        <div className="flex items-center gap-2">
          <label htmlFor="date-select" className="text-sm text-muted-foreground">
            Date:
          </label>
          <select
            id="date-select"
            value={selectedDate}
            onChange={handleDateChange}
            disabled={isLoading || availableDates.length === 0}
            className="px-3 py-1.5 bg-background border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
          >
            {availableDates.length === 0 ? (
              <option value="">No data available</option>
            ) : (
              availableDates.map((date) => (
                <option key={date} value={date}>
                  {formatDisplayDate(date)}
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-600">
          {error}
        </div>
      )}

      {/* Stats */}
      {tagsData && !isLoading && (
        <div className="flex gap-4 text-sm">
          <div className="px-4 py-2 bg-muted/50 rounded-lg">
            <span className="text-muted-foreground">Total: </span>
            <span className="font-medium">{tagsData.count}</span>
          </div>
          <div className="px-4 py-2 bg-amber-500/10 rounded-lg">
            <span className="text-amber-600">Pending: </span>
            <span className="font-medium text-amber-600">{pendingCount}</span>
          </div>
          <div className="px-4 py-2 bg-green-500/10 rounded-lg">
            <span className="text-green-600">Reviewed: </span>
            <span className="font-medium text-green-600">{reviewedCount}</span>
          </div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="py-8 text-center text-muted-foreground">
          Loading tags...
        </div>
      )}

      {/* Tag list */}
      {!isLoading && tagsData && (
        <TagReviewList data={tagsData.data} onUpdate={handleTagUpdate} />
      )}
    </main>
  );
}
