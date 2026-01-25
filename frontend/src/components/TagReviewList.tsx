"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Clock, CheckCircle, Circle, Pencil } from "lucide-react";
import { TagEditModal } from "./TagEditModal";

interface TagReview {
  id: string;
  tag_id?: string;
  record_date?: string;
  timestamp: number;
  datetime_utc?: string;
  emotion_label: string | null;
  stress_level: number | null;
  video_url: string | null;
  reviewed: boolean;
  created_at: string;
}

interface TagReviewListProps {
  data: TagReview[];
  onUpdate?: () => void;
}

function formatTime(tag: TagReview): string {
  // Use datetime_utc if available, fallback to timestamp
  if (tag.datetime_utc) {
    const date = new Date(tag.datetime_utc);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  // Fallback for old data format
  const date = new Date(tag.timestamp * 1000);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function TagReviewList({ data: initialData, onUpdate }: TagReviewListProps) {
  const [data, setData] = useState<TagReview[]>(initialData);
  const [selectedTag, setSelectedTag] = useState<TagReview | null>(null);

  // Update data when initialData changes
  if (initialData !== data && initialData.length > 0) {
    setData(initialData);
  }

  const handleSave = async (updates: Partial<TagReview>) => {
    if (!selectedTag) return;

    const res = await fetch("/api/wellness", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reviewId: selectedTag.id, ...updates }),
    });

    if (res.ok) {
      const { data: updatedTag } = await res.json();
      setData((prev) =>
        prev.map((tag) => (tag.id === selectedTag.id ? { ...tag, ...updatedTag } : tag))
      );
      // Notify parent to refresh data
      onUpdate?.();
    }
  };

  if (data.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No tagged events found for this date.
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="space-y-4">
        {data.map((tag, index) => (
          <Card
            key={tag.id || `tag-${tag.timestamp}-${index}`}
            className="cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => setSelectedTag(tag)}
          >
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  {formatTime(tag)}
                </CardTitle>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    {tag.reviewed ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <Circle className="h-4 w-4 text-muted-foreground" />
                    )}
                    <span className="text-sm text-muted-foreground">
                      {tag.reviewed ? "Reviewed" : "Pending"}
                    </span>
                  </div>
                  <Pencil className="h-4 w-4 text-muted-foreground" />
                </div>
              </div>
              {tag.emotion_label && (
                <CardDescription>{tag.emotion_label}</CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4 text-sm">
                {tag.stress_level !== null && (
                  <div>
                    <span className="text-muted-foreground">Stress Level: </span>
                    <span className="font-medium">{tag.stress_level}/10</span>
                  </div>
                )}
                {tag.video_url && (
                  <a
                    href={tag.video_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary underline-offset-4 hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    View Video
                  </a>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {selectedTag && (
        <TagEditModal
          tag={selectedTag}
          isOpen={!!selectedTag}
          onClose={() => setSelectedTag(null)}
          onSave={handleSave}
        />
      )}
    </>
  );
}
