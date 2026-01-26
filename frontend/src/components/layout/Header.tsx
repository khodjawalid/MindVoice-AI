"use client";

import Link from "next/link";
import { motion } from "framer-motion";

interface HeaderProps {
  variant?: "default" | "dashboard";
  userName?: string;
}

export function Header({ variant = "default", userName }: HeaderProps) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border"
    >
      <div className="container mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="font-serif text-xl font-semibold text-foreground">
          MindVoice
        </Link>

        {variant === "dashboard" && userName && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-sage/20 flex items-center justify-center">
              <span className="text-sm font-medium text-sage">
                {userName.charAt(0).toUpperCase()}
              </span>
            </div>
          </div>
        )}
      </div>
    </motion.header>
  );
}
