"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Video, Brain, Tag } from "lucide-react";

interface VideoInference {
  id: string;
  tag_id: string;
  record_date: string;
  predicted_emotion: string;
  pred_confidence: number;
  emotion_probabilities: Record<string, number>;
  created_at: string;
}

interface TagData {
  id: string;
  datetime_utc?: string;
  timestamp?: number;
  emotion_label?: string;
  stress_level?: number;
}

interface VideoInferenceChartProps {
  inferences: VideoInference[];
  date: string;
  tags?: TagData[];
}

// Emotion colors for visualization
const emotionColors: Record<string, { bg: string; bar: string; text: string }> = {
  anger: { bg: "bg-red-100", bar: "bg-red-500", text: "text-red-800" },
  calm: { bg: "bg-blue-100", bar: "bg-blue-500", text: "text-blue-800" },
  contempt: { bg: "bg-purple-100", bar: "bg-purple-500", text: "text-purple-800" },
  disgust: { bg: "bg-green-100", bar: "bg-green-500", text: "text-green-800" },
  fear: { bg: "bg-yellow-100", bar: "bg-yellow-500", text: "text-yellow-800" },
  happy: { bg: "bg-amber-100", bar: "bg-amber-500", text: "text-amber-800" },
  neutral: { bg: "bg-gray-100", bar: "bg-gray-500", text: "text-gray-800" },
  sad: { bg: "bg-indigo-100", bar: "bg-indigo-500", text: "text-indigo-800" },
  surprise: { bg: "bg-pink-100", bar: "bg-pink-500", text: "text-pink-800" },
};

// Canonical order for emotions
const emotionOrder = [
  "happy",
  "calm",
  "neutral",
  "surprise",
  "sad",
  "fear",
  "anger",
  "disgust",
  "contempt",
];

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getTagTime(tag: TagData): string {
  if (tag.datetime_utc) {
    return formatTime(tag.datetime_utc);
  }
  if (tag.timestamp) {
    return formatTime(new Date(tag.timestamp * 1000).toISOString());
  }
  return "Unknown";
}

export function VideoInferenceChart({ inferences, date, tags = [] }: VideoInferenceChartProps) {
  // Create a map for quick tag lookup
  const tagMap = new Map(tags.map((tag) => [tag.id, tag]));

  if (inferences.length === 0) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Video className="h-5 w-5 text-muted-foreground" />
            <CardTitle>Video Emotion Analysis</CardTitle>
          </div>
          <CardDescription>
            No video responses recorded for {date}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-32 text-muted-foreground">
            <p className="text-sm">Record video responses in the Wellness page to see analysis here</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Aggregate emotion probabilities across all inferences
  const aggregatedEmotions: Record<string, number[]> = {};
  emotionOrder.forEach((emotion) => {
    aggregatedEmotions[emotion] = [];
  });

  inferences.forEach((inference) => {
    Object.entries(inference.emotion_probabilities)
      .filter(([emotion]) => emotion && emotion.trim() !== "")
      .forEach(([emotion, prob]) => {
        if (aggregatedEmotions[emotion]) {
          aggregatedEmotions[emotion].push(prob);
        }
      });
  });

  // Calculate average for each emotion
  const avgEmotions = emotionOrder.map((emotion) => {
    const values = aggregatedEmotions[emotion];
    const avg = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : 0;
    return { emotion, avg };
  });

  // Find dominant emotion
  const dominantEmotion = avgEmotions.reduce((max, curr) =>
    curr.avg > max.avg ? curr : max
  );

  // Sort inferences by tag time (using tag's datetime_utc)
  const sortedInferences = [...inferences].sort((a, b) => {
    const tagA = tagMap.get(a.tag_id);
    const tagB = tagMap.get(b.tag_id);
    const timeA = tagA?.datetime_utc || tagA?.timestamp || a.created_at;
    const timeB = tagB?.datetime_utc || tagB?.timestamp || b.created_at;
    return new Date(timeA).getTime() - new Date(timeB).getTime();
  });

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            <CardTitle>Video Emotion Analysis</CardTitle>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold capitalize">
              {dominantEmotion.emotion}
            </div>
            <div className="text-xs text-muted-foreground">
              Dominant emotion • {inferences.length} recording{inferences.length > 1 ? "s" : ""}
            </div>
          </div>
        </div>
        <CardDescription>
          Multimodal inference from video responses (vision + audio)
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Individual Tag Recordings - Primary View */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <Tag className="h-4 w-4" />
            Per-Tag Analysis
          </h4>
          <div className="space-y-3">
            {sortedInferences.map((inference) => {
              const tag = tagMap.get(inference.tag_id);
              const tagTime = tag ? getTagTime(tag) : formatTime(inference.created_at);

              return (
                <div
                  key={inference.id}
                  className="border rounded-lg p-3 space-y-2"
                >
                  {/* Tag Header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono text-muted-foreground">
                        Tag @ {tagTime}
                      </span>
                      {tag?.emotion_label && (
                        <span className="px-2 py-0.5 text-xs rounded bg-blue-100 text-blue-800">
                          {tag.emotion_label}
                        </span>
                      )}
                      {tag?.stress_level !== undefined && (
                        <span className={`px-2 py-0.5 text-xs rounded ${
                          tag.stress_level > 5
                            ? "bg-red-100 text-red-800"
                            : tag.stress_level > 3
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-green-100 text-green-800"
                        }`}>
                          Stress: {tag.stress_level}/10
                        </span>
                      )}
                    </div>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium capitalize ${
                        emotionColors[inference.predicted_emotion]?.bg || "bg-gray-100"
                      } ${emotionColors[inference.predicted_emotion]?.text || "text-gray-800"}`}
                    >
                      {inference.predicted_emotion} ({(inference.pred_confidence * 100).toFixed(0)}%)
                    </span>
                  </div>

                  {/* Top 3 Emotions for this tag */}
                  <div className="space-y-1">
                    {Object.entries(inference.emotion_probabilities)
                      .filter(([emotion]) => emotion && emotion.trim() !== "")
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 3)
                      .map(([emotion, prob], index) => (
                        <div key={emotion || `emotion-${index}`} className="flex items-center gap-2 text-xs">
                          <span className="w-16 capitalize truncate text-muted-foreground">{emotion}</span>
                          <div className="flex-1 bg-muted rounded-full h-1.5 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                emotionColors[emotion]?.bar || "bg-gray-400"
                              }`}
                              style={{ width: `${prob * 100}%` }}
                            />
                          </div>
                          <span className="w-10 text-right text-muted-foreground">
                            {(prob * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Aggregated Summary - Secondary */}
        {inferences.length > 1 && (
          <div className="border-t pt-4">
            <h4 className="text-sm font-medium text-muted-foreground mb-3">
              Daily Average
            </h4>
            <div className="space-y-1.5">
              {avgEmotions
                .filter(({ avg }) => avg > 0.01)
                .sort((a, b) => b.avg - a.avg)
                .slice(0, 5)
                .map(({ emotion, avg }) => (
                  <div key={emotion} className="flex items-center gap-3">
                    <span className="w-20 text-xs capitalize truncate text-muted-foreground">{emotion}</span>
                    <div className="flex-1 bg-muted rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          emotionColors[emotion]?.bar || "bg-gray-400"
                        }`}
                        style={{ width: `${avg * 100}%` }}
                      />
                    </div>
                    <span className="w-10 text-right text-xs text-muted-foreground">
                      {(avg * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
