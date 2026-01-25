"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, Video, CheckCircle, AlertCircle } from "lucide-react";
import { EmotionSelector } from "./EmotionSelector";
import { StressLevelSelector } from "./StressLevelSelector";
import { VideoRecorder } from "./VideoRecorder";

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
}

interface VideoInferenceResult {
  id: string;
  tag_id: string;
  predicted_emotion: string;
  pred_confidence: number;
  emotion_probabilities: Record<string, number>;
}

interface TagEditModalProps {
  tag: TagReview;
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: Partial<TagReview>) => Promise<void>;
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

// Emotion color mapping for displaying inference results
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

export function TagEditModal({ tag, isOpen, onClose, onSave }: TagEditModalProps) {
  const [emotionLabel, setEmotionLabel] = useState<string | null>(tag.emotion_label);
  const [stressLevel, setStressLevel] = useState<number | null>(tag.stress_level);
  const [videoUrl, setVideoUrl] = useState(tag.video_url || "");
  const [reviewed, setReviewed] = useState(tag.reviewed);
  const [isSaving, setIsSaving] = useState(false);

  // Video recording state
  const [showVideoRecorder, setShowVideoRecorder] = useState(false);
  const [isProcessingVideo, setIsProcessingVideo] = useState(false);
  const [inferenceResult, setInferenceResult] = useState<VideoInferenceResult | null>(null);
  const [inferenceError, setInferenceError] = useState<string | null>(null);

  // Load existing inference result when modal opens
  useEffect(() => {
    if (isOpen && tag.id) {
      loadExistingInference();
    }
  }, [isOpen, tag.id]);

  const loadExistingInference = async () => {
    try {
      const response = await fetch(`/api/wellness/tags/${tag.id}/inference`);
      if (response.ok) {
        const data = await response.json();
        if (data.data) {
          setInferenceResult(data.data);
        }
      }
    } catch (error) {
      console.error("Failed to load existing inference:", error);
    }
  };

  const handleVideoRecordingComplete = async (videoBlob: Blob) => {
    setIsProcessingVideo(true);
    setInferenceError(null);

    try {
      const formData = new FormData();
      formData.append("video", videoBlob, "recording.webm");

      const response = await fetch(`/api/wellness/tags/${tag.id}/inference`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Inference failed");
      }

      const result = await response.json();
      setInferenceResult(result);
    } catch (error) {
      console.error("Video inference error:", error);
      setInferenceError(error instanceof Error ? error.message : "Failed to process video");
    } finally {
      setIsProcessingVideo(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave({
        emotion_label: emotionLabel,
        stress_level: stressLevel,
        video_url: videoUrl || null,
        reviewed,
      });
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  // Auto-enable reviewed checkbox when inference is complete
  const canMarkReviewed = inferenceResult !== null || tag.reviewed;

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="tag-edit-modal"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            {/* Overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/50"
              onClick={onClose}
            />

            {/* Modal */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.2 }}
              className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-background rounded-2xl shadow-xl"
            >
              {/* Header */}
              <div className="sticky top-0 bg-background border-b px-6 py-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold">
                  Edit Tag - {formatTime(tag)}
                </h2>
                <button
                  onClick={onClose}
                  className="p-2 rounded-full hover:bg-muted transition-colors"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Content */}
              <div className="p-6 space-y-6">
                {/* Video Response Section */}
                <div className="border rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="block text-sm font-medium">
                      Video Response
                    </label>
                    {inferenceResult && (
                      <span className="text-xs text-green-600 flex items-center gap-1">
                        <CheckCircle className="h-3 w-3" />
                        Completed
                      </span>
                    )}
                  </div>

                  {isProcessingVideo ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="text-center">
                        <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
                        <p className="mt-2 text-sm text-muted-foreground">
                          Analyzing your response...
                        </p>
                      </div>
                    </div>
                  ) : inferenceResult ? (
                    <div className="space-y-3">
                      {/* Inference Result Display */}
                      <div className="bg-muted/50 rounded-lg p-3">
                        <p className="text-xs text-muted-foreground mb-2">
                          Detected emotion:
                        </p>
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${
                              emotionColors[inferenceResult.predicted_emotion] || "bg-gray-100"
                            }`}
                          >
                            {inferenceResult.predicted_emotion}
                          </span>
                          <span className="text-sm text-muted-foreground">
                            {(inferenceResult.pred_confidence * 100).toFixed(0)}% confidence
                          </span>
                        </div>

                        {/* Top 3 emotions bar */}
                        <div className="mt-3 space-y-1.5">
                          {Object.entries(inferenceResult.emotion_probabilities)
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
                      </div>

                      <button
                        onClick={() => setShowVideoRecorder(true)}
                        className="w-full px-4 py-2 text-sm rounded-lg border hover:bg-muted transition-colors"
                      >
                        Record Again
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {inferenceError && (
                        <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-lg p-3">
                          <AlertCircle className="h-4 w-4 flex-shrink-0" />
                          <p>{inferenceError}</p>
                        </div>
                      )}

                      <p className="text-sm text-muted-foreground">
                        Record a short video describing what happened at this moment.
                        This helps us understand your emotional state better.
                      </p>

                      <button
                        onClick={() => setShowVideoRecorder(true)}
                        className="w-full px-4 py-3 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
                      >
                        <Video className="h-4 w-4" />
                        Record Video Response
                      </button>
                    </div>
                  )}
                </div>

                {/* Emotion Selector */}
                <div>
                  <label className="block text-sm font-medium mb-3">
                    How were you feeling?
                  </label>
                  <EmotionSelector
                    selectedEmotion={emotionLabel}
                    onSelect={setEmotionLabel}
                  />
                </div>

                {/* Stress Level */}
                <div>
                  <label className="block text-sm font-medium mb-3">
                    Stress Level (1-10)
                  </label>
                  <StressLevelSelector
                    selectedLevel={stressLevel}
                    onSelect={setStressLevel}
                  />
                </div>

                {/* Video URL (optional, kept for backward compatibility) */}
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Video URL (optional)
                  </label>
                  <input
                    type="url"
                    value={videoUrl}
                    onChange={(e) => setVideoUrl(e.target.value)}
                    placeholder="https://..."
                    className="w-full px-4 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>

                {/* Reviewed Checkbox */}
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="reviewed"
                    checked={reviewed}
                    onChange={(e) => setReviewed(e.target.checked)}
                    disabled={!canMarkReviewed && !reviewed}
                    className="w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary disabled:opacity-50"
                  />
                  <label htmlFor="reviewed" className="text-sm font-medium">
                    Mark as reviewed
                  </label>
                  {!canMarkReviewed && !reviewed && (
                    <span className="text-xs text-muted-foreground">
                      (Record video first)
                    </span>
                  )}
                </div>
              </div>

              {/* Footer */}
              <div className="sticky bottom-0 bg-background border-t px-6 py-4 flex gap-3 justify-end">
                <button
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg border hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {isSaving && <Loader2 className="h-4 w-4 animate-spin" />}
                  Save
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Video Recorder Modal */}
      <VideoRecorder
        isOpen={showVideoRecorder}
        onClose={() => setShowVideoRecorder(false)}
        onRecordingComplete={handleVideoRecordingComplete}
        maxDuration={30}
        prompt="Could you describe what happened?"
      />
    </>
  );
}
