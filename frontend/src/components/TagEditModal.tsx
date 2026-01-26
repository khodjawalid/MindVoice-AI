"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2 } from "lucide-react";
import { EmotionSelector } from "./EmotionSelector";
import { StressLevelSelector } from "./StressLevelSelector";
import { Button } from "@/components/ui/button";

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

interface TagEditModalProps {
  tag: TagReview;
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: Partial<TagReview>) => Promise<void>;
}

function formatTime(tag: TagReview): string {
  if (tag.datetime_utc) {
    const date = new Date(tag.datetime_utc);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  const date = new Date(tag.timestamp * 1000);
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function TagEditModal({ tag, isOpen, onClose, onSave }: TagEditModalProps) {
  const [emotionLabel, setEmotionLabel] = useState<string | null>(tag.emotion_label);
  const [stressLevel, setStressLevel] = useState<number | null>(tag.stress_level);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave({
        emotion_label: emotionLabel,
        stress_level: stressLevel,
        reviewed: true, // Auto-mark as reviewed when saved
      });
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  // Check if form is complete
  const isComplete = emotionLabel !== null && stressLevel !== null;

  return (
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
                Review Tag - {formatTime(tag)}
              </h2>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="h-5 w-5" />
              </Button>
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

              {/* Hint about daily video */}
              <div className="text-sm text-muted-foreground bg-muted/50 rounded-lg p-3">
                After reviewing all tags for today, you&apos;ll be prompted to record
                a daily video summary.
              </div>
            </div>

            {/* Footer */}
            <div className="sticky bottom-0 bg-background border-t px-6 py-4 flex gap-3 justify-end">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={isSaving || !isComplete}
                variant="sage"
              >
                {isSaving && <Loader2 className="h-4 w-4 animate-spin" />}
                {isComplete ? "Save & Mark Reviewed" : "Select emotion & stress"}
              </Button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
