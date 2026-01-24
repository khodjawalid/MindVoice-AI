"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2 } from "lucide-react";
import { EmotionSelector } from "./EmotionSelector";
import { StressLevelSelector } from "./StressLevelSelector";

interface TagReview {
  id: string;
  timestamp_unix: number;
  emotion_label: string | null;
  stress_level: number | null;
  video_url: string | null;
  reviewed: boolean;
}

interface TagEditModalProps {
  tag: TagReview;
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: Partial<TagReview>) => Promise<void>;
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function TagEditModal({ tag, isOpen, onClose, onSave }: TagEditModalProps) {
  const [emotionLabel, setEmotionLabel] = useState<string | null>(tag.emotion_label);
  const [stressLevel, setStressLevel] = useState<number | null>(tag.stress_level);
  const [videoUrl, setVideoUrl] = useState(tag.video_url || "");
  const [reviewed, setReviewed] = useState(tag.reviewed);
  const [isSaving, setIsSaving] = useState(false);

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

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
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
                Edit Tag - {formatTime(tag.timestamp_unix)}
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

              {/* Video URL */}
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
                  className="w-5 h-5 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <label htmlFor="reviewed" className="text-sm font-medium">
                  Mark as reviewed
                </label>
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
  );
}
