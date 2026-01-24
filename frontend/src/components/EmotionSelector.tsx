"use client";

import { motion } from "framer-motion";

const emotions = [
  { emoji: "😊", label: "Happy", color: "bg-green-100 hover:bg-green-200 border-green-200" },
  { emoji: "😢", label: "Sad", color: "bg-blue-100 hover:bg-blue-200 border-blue-200" },
  { emoji: "😰", label: "Anxious", color: "bg-amber-100 hover:bg-amber-200 border-amber-200" },
  { emoji: "😤", label: "Frustrated", color: "bg-red-100 hover:bg-red-200 border-red-200" },
  { emoji: "😌", label: "Calm", color: "bg-teal-100 hover:bg-teal-200 border-teal-200" },
  { emoji: "😔", label: "Stressed", color: "bg-purple-100 hover:bg-purple-200 border-purple-200" },
  { emoji: "🥰", label: "Loved", color: "bg-pink-100 hover:bg-pink-200 border-pink-200" },
  { emoji: "😐", label: "Neutral", color: "bg-gray-100 hover:bg-gray-200 border-gray-200" },
];

interface EmotionSelectorProps {
  selectedEmotion: string | null;
  onSelect: (emotion: string) => void;
}

export function EmotionSelector({ selectedEmotion, onSelect }: EmotionSelectorProps) {
  return (
    <div className="grid grid-cols-4 gap-3">
      {emotions.map((emotion, index) => (
        <motion.button
          key={emotion.label}
          type="button"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: index * 0.05 }}
          onClick={() => onSelect(emotion.label)}
          className={`flex flex-col items-center gap-2 p-4 rounded-2xl border-2 transition-all duration-200 cursor-pointer ${
            selectedEmotion === emotion.label
              ? `${emotion.color} border-primary ring-2 ring-primary/20`
              : `${emotion.color} border-transparent`
          }`}
        >
          <span className="text-3xl">{emotion.emoji}</span>
          <span className="text-sm font-medium text-foreground">{emotion.label}</span>
        </motion.button>
      ))}
    </div>
  );
}
