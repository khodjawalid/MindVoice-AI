"use client";

import { motion } from "framer-motion";

interface StressLevelSelectorProps {
  selectedLevel: number | null;
  onSelect: (level: number) => void;
}

const levels = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

function getLevelColor(level: number, isSelected: boolean): string {
  const baseColors: Record<number, string> = {
    1: "bg-green-100 hover:bg-green-200",
    2: "bg-green-100 hover:bg-green-200",
    3: "bg-lime-100 hover:bg-lime-200",
    4: "bg-yellow-100 hover:bg-yellow-200",
    5: "bg-yellow-100 hover:bg-yellow-200",
    6: "bg-amber-100 hover:bg-amber-200",
    7: "bg-orange-100 hover:bg-orange-200",
    8: "bg-orange-100 hover:bg-orange-200",
    9: "bg-red-100 hover:bg-red-200",
    10: "bg-red-100 hover:bg-red-200",
  };

  const selectedColors: Record<number, string> = {
    1: "bg-green-200 ring-2 ring-green-400",
    2: "bg-green-200 ring-2 ring-green-400",
    3: "bg-lime-200 ring-2 ring-lime-400",
    4: "bg-yellow-200 ring-2 ring-yellow-400",
    5: "bg-yellow-200 ring-2 ring-yellow-400",
    6: "bg-amber-200 ring-2 ring-amber-400",
    7: "bg-orange-200 ring-2 ring-orange-400",
    8: "bg-orange-200 ring-2 ring-orange-400",
    9: "bg-red-200 ring-2 ring-red-400",
    10: "bg-red-200 ring-2 ring-red-400",
  };

  return isSelected ? selectedColors[level] : baseColors[level];
}

export function StressLevelSelector({ selectedLevel, onSelect }: StressLevelSelectorProps) {
  return (
    <div className="flex gap-2 flex-wrap justify-center">
      {levels.map((level, index) => (
        <motion.button
          key={level}
          type="button"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.2, delay: index * 0.03 }}
          onClick={() => onSelect(level)}
          className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm transition-all duration-200 cursor-pointer ${getLevelColor(
            level,
            selectedLevel === level
          )}`}
        >
          {level}
        </motion.button>
      ))}
    </div>
  );
}
