"use client";

import { useEffect, useState, useCallback } from "react";
import { TagReviewList } from "@/components/TagReviewList";
import { VideoRecorder } from "@/components/VideoRecorder";
import Link from "next/link";
import { Video, CheckCircle, Loader2, AlertCircle, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

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

interface DailyInference {
  id: string;
  record_date: string;
  predicted_emotion: string;
  pred_confidence: number;
  emotion_probabilities: Record<string, number>;
}

// Emotion color mapping
const emotionColors: Record<string, string> = {
  anger: "bg-red-100 text-red-800",
  calm: "bg-blue-100 text-blue-800",
  contempt: "bg-purple-100 text-purple-800",
  disgust: "bg-green-100 text-green-800",
  fear: "bg-yellow-100 text-yellow-800",
  happy: "bg-amber-100 text-amber-800",
  neutral: "bg-gray-100 text-gray-800",
  sad: "bg-indigo-100 text-indigo-800",
  surprise: "bg-pink-100 text-pink-800",
};

export default function WellnessPage() {
  const [availableDates, setAvailableDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [tagsData, setTagsData] = useState<TagsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Daily video state
  const [dailyInference, setDailyInference] = useState<DailyInference | null>(null);
  const [showVideoRecorder, setShowVideoRecorder] = useState(false);
  const [isProcessingVideo, setIsProcessingVideo] = useState(false);
  const [videoError, setVideoError] = useState<string | null>(null);

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

  // Fetch daily inference when date changes
  const fetchDailyInference = useCallback(async (date: string) => {
    try {
      const res = await fetch(`/api/wellness/daily-inference?date=${date}`);
      if (res.ok) {
        const data = await res.json();
        setDailyInference(data.data);
      }
    } catch (err) {
      console.error("Error fetching daily inference:", err);
    }
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
      // Also fetch daily inference
      if (data.date) {
        fetchDailyInference(data.date);
      }
    } catch (err) {
      console.error("Error fetching tags:", err);
      setError("Failed to load tags");
    } finally {
      setIsLoading(false);
    }
  }, [fetchDailyInference]);

  // Initial fetch
  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  // Refresh data after update
  const handleTagUpdate = () => {
    if (selectedDate) {
      fetchTags(selectedDate);
    }
  };

  // Handle daily video recording complete
  const handleVideoRecordingComplete = async (videoBlob: Blob) => {
    if (!selectedDate) return;

    setIsProcessingVideo(true);
    setVideoError(null);

    try {
      const formData = new FormData();
      formData.append("video", videoBlob, "daily-recording.webm");

      const response = await fetch(`/api/wellness/daily-inference?date=${selectedDate}`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Inference failed");
      }

      const result = await response.json();
      setDailyInference(result);
      setShowVideoRecorder(false);
    } catch (error) {
      console.error("Daily video inference error:", error);
      setVideoError(error instanceof Error ? error.message : "Failed to process video");
    } finally {
      setIsProcessingVideo(false);
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
  const allTagsReviewed = tagsData && tagsData.count > 0 && pendingCount === 0;

  return (
    <main className="p-8 max-w-4xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/">
              <ArrowLeft className="w-5 h-5" />
            </Link>
          </Button>
          <h1 className="text-2xl font-bold">Wellness Tags</h1>
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
                setDailyInference(null);
                fetchTags(value);
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

      {/* Stats */}
      {tagsData && !isLoading && (
        <div className="flex flex-wrap gap-3">
          <Badge variant="secondary" className="px-4 py-2 text-sm">
            Total: {tagsData.count}
          </Badge>
          <Badge variant="warning" className="px-4 py-2 text-sm">
            Pending: {pendingCount}
          </Badge>
          <Badge variant="success" className="px-4 py-2 text-sm">
            Reviewed: {reviewedCount}
          </Badge>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
        </div>
      )}

      {/* Tag list */}
      {!isLoading && tagsData && (
        <TagReviewList data={tagsData.data} onUpdate={handleTagUpdate} />
      )}

      {/* Daily Video Section - shows when all tags are reviewed */}
      {!isLoading && tagsData && tagsData.count > 0 && (
        <div className="border-t pt-8">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Video className="h-5 w-5" />
            Daily Video Summary
          </h2>

          {!allTagsReviewed ? (
            <div className="bg-muted/50 rounded-xl p-6 text-center">
              <p className="text-muted-foreground">
                Review all {pendingCount} remaining tag{pendingCount !== 1 ? "s" : ""} to unlock
                the daily video recording.
              </p>
            </div>
          ) : isProcessingVideo ? (
            <div className="bg-muted/50 rounded-xl p-8 text-center">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <p className="mt-3 text-muted-foreground">
                Analyzing your daily video...
              </p>
            </div>
          ) : dailyInference ? (
            <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <span className="font-medium text-green-600">Daily video recorded</span>
              </div>

              {/* Inference Result Display */}
              <div className="bg-background rounded-lg p-4">
                <p className="text-xs text-muted-foreground mb-2">
                  Detected emotion:
                </p>
                <div className="flex items-center gap-2 mb-3">
                  <span
                    className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${
                      emotionColors[dailyInference.predicted_emotion] || "bg-gray-100"
                    }`}
                  >
                    {dailyInference.predicted_emotion}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {(dailyInference.pred_confidence * 100).toFixed(0)}% confidence
                  </span>
                </div>

                {/* Top 3 emotions bar */}
                <div className="space-y-1.5">
                  {Object.entries(dailyInference.emotion_probabilities)
                    .filter(([emotion]) => emotion && emotion.trim() !== "")
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 3)
                    .map(([emotion, prob], index) => (
                      <div key={emotion || `emotion-${index}`} className="flex items-center gap-2 text-xs">
                        <span className="w-16 capitalize truncate">{emotion}</span>
                        <div className="flex-1 bg-muted rounded-full h-2 overflow-hidden">
                          <div
                            className="h-full bg-primary/60 rounded-full transition-all"
                            style={{ width: `${prob * 100}%` }}
                          />
                        </div>
                        <span className="w-10 text-right text-muted-foreground">
                          {(prob * 100).toFixed(0)}%
                        </span>
                      </div>
                    ))}
                </div>

                <Button
                  onClick={() => setShowVideoRecorder(true)}
                  variant="outline"
                  className="mt-4 w-full"
                >
                  Record Again
                </Button>
              </div>
            </div>
          ) : (
            <div className="bg-primary/5 border border-primary/20 rounded-xl p-6 text-center space-y-4">
              {videoError && (
                <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg p-3 mb-4">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <p>{videoError}</p>
                </div>
              )}

              <p className="text-muted-foreground">
                All tags reviewed! Record a short video describing how your day went overall.
              </p>

              <Button
                onClick={() => setShowVideoRecorder(true)}
                variant="sage"
                size="lg"
                className="mx-auto"
              >
                <Video className="h-4 w-4" />
                Record Daily Video
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Video Recorder Modal */}
      <VideoRecorder
        isOpen={showVideoRecorder}
        onClose={() => setShowVideoRecorder(false)}
        onRecordingComplete={handleVideoRecordingComplete}
        maxDuration={30}
        prompt="How was your day overall?"
      />
    </main>
  );
}
