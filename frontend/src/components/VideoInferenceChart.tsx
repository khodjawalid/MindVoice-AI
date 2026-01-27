"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Video, Brain, ChevronDown, ChevronUp, Eye, Mic } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface DailyInference {
  id: string;
  record_date: string;
  predicted_emotion: string;
  pred_confidence: number;
  emotion_probabilities: Record<string, number>;
  created_at?: string;
  backend?: string;
  raw_face_emotions?: Record<string, number>;
  raw_prosody_emotions?: Record<string, number>;
}

interface VideoInferenceChartProps {
  dailyInference: DailyInference | null;
  date: string;
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

// Helper to get top N emotions from a record
function getTopEmotions(emotions: Record<string, number> | undefined, count: number = 5) {
  if (!emotions) return [];
  return Object.entries(emotions)
    .filter(([emotion, score]) => emotion && score > 0)
    .sort(([, a], [, b]) => b - a)
    .slice(0, count);
}

export function VideoInferenceChart({ dailyInference, date }: VideoInferenceChartProps) {
  const [showDetails, setShowDetails] = useState(false);

  if (!dailyInference) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Video className="h-5 w-5 text-muted-foreground" />
            <CardTitle>Daily Emotion Analysis</CardTitle>
          </div>
          <CardDescription>
            No daily video recorded for {date}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center h-32 text-muted-foreground gap-3">
            <p className="text-sm">Record a daily video in the Wellness page to see analysis here</p>
            <Link
              href="/wellness"
              className="text-sm text-primary hover:underline"
            >
              Go to Wellness →
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Sort emotions by probability (show all 9)
  const sortedEmotions = emotionOrder
    .map((emotion) => ({
      emotion,
      prob: dailyInference.emotion_probabilities[emotion] || 0,
    }))
    .sort((a, b) => b.prob - a.prob);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            <CardTitle>Daily Emotion Analysis</CardTitle>
          </div>
          <div className="text-right">
            <div
              className={`inline-block px-3 py-1 rounded-full text-lg font-bold capitalize ${
                emotionColors[dailyInference.predicted_emotion]?.bg || "bg-gray-100"
              } ${emotionColors[dailyInference.predicted_emotion]?.text || "text-gray-800"}`}
            >
              {dailyInference.predicted_emotion}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {(dailyInference.pred_confidence * 100).toFixed(0)}% confidence
            </div>
          </div>
        </div>
        <CardDescription className="flex items-center gap-2">
          Multimodal inference from daily video (vision + audio)
          {dailyInference.backend === "hume" && (
            <Badge variant="secondary" className="text-xs">
              Hume AI
            </Badge>
          )}
          {dailyInference.backend === "local" && (
            <Badge variant="outline" className="text-xs">
              Local Models
            </Badge>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* All Emotions Chart */}
        <div className="space-y-2">
          {sortedEmotions.map(({ emotion, prob }) => (
            <div key={emotion} className="flex items-center gap-3">
              <span className="w-20 text-sm capitalize truncate text-muted-foreground">
                {emotion}
              </span>
              <div className="flex-1 bg-muted rounded-full h-3 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    emotionColors[emotion]?.bar || "bg-gray-400"
                  }`}
                  style={{ width: `${prob * 100}%` }}
                />
              </div>
              <span className="w-12 text-right text-sm text-muted-foreground">
                {(prob * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>

        {/* Face vs Prosody Breakdown (only for Hume backend) */}
        {dailyInference.backend === "hume" &&
          (dailyInference.raw_face_emotions || dailyInference.raw_prosody_emotions) && (
            <div className="border-t pt-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDetails(!showDetails)}
                className="w-full flex items-center justify-center gap-2 text-muted-foreground hover:text-foreground"
              >
                {showDetails ? (
                  <>
                    <ChevronUp className="h-4 w-4" />
                    Hide Face & Audio Details
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-4 w-4" />
                    Show Face & Audio Details
                  </>
                )}
              </Button>

              {showDetails && (
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Face Analysis Column */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm font-medium text-blue-700">
                      <Eye className="h-4 w-4" />
                      Face Analysis
                    </div>
                    <div className="space-y-1.5">
                      {getTopEmotions(dailyInference.raw_face_emotions, 5).map(
                        ([emotion, score]) => (
                          <div key={emotion} className="flex items-center gap-2 text-xs">
                            <span className="w-24 capitalize truncate">{emotion}</span>
                            <div className="flex-1 bg-blue-100 rounded-full h-2 overflow-hidden">
                              <div
                                className="h-full bg-blue-500 rounded-full transition-all"
                                style={{ width: `${score * 100}%` }}
                              />
                            </div>
                            <span className="w-10 text-right text-muted-foreground">
                              {(score * 100).toFixed(0)}%
                            </span>
                          </div>
                        )
                      )}
                      {getTopEmotions(dailyInference.raw_face_emotions, 5).length === 0 && (
                        <p className="text-xs text-muted-foreground">No face detected</p>
                      )}
                    </div>
                  </div>

                  {/* Prosody Analysis Column */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm font-medium text-purple-700">
                      <Mic className="h-4 w-4" />
                      Audio Analysis
                    </div>
                    <div className="space-y-1.5">
                      {getTopEmotions(dailyInference.raw_prosody_emotions, 5).map(
                        ([emotion, score]) => (
                          <div key={emotion} className="flex items-center gap-2 text-xs">
                            <span className="w-24 capitalize truncate">{emotion}</span>
                            <div className="flex-1 bg-purple-100 rounded-full h-2 overflow-hidden">
                              <div
                                className="h-full bg-purple-500 rounded-full transition-all"
                                style={{ width: `${score * 100}%` }}
                              />
                            </div>
                            <span className="w-10 text-right text-muted-foreground">
                              {(score * 100).toFixed(0)}%
                            </span>
                          </div>
                        )
                      )}
                      {getTopEmotions(dailyInference.raw_prosody_emotions, 5).length === 0 && (
                        <p className="text-xs text-muted-foreground">No speech detected</p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
      </CardContent>
    </Card>
  );
}
