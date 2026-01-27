"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ArrowUpRight } from "lucide-react";

interface HeaderProps {
  variant?: "default" | "dashboard" | "landing";
  userName?: string;
}

export function Header({ variant = "default", userName }: HeaderProps) {
  // Landing page header - transparent with login button
  if (variant === "landing") {
    return (
      <motion.header
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-sm"
      >
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/landing" className="text-2xl font-serif font-semibold text-foreground">
            MindVoice
          </Link>
          <Button asChild className="rounded-full px-6 bg-sage hover:bg-sage-dark text-white">
            <Link href="/home">
              Login
              <ArrowUpRight className="ml-2 w-4 h-4" />
            </Link>
          </Button>
        </div>
      </motion.header>
    );
  }

  return (
    <motion.header
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border"
    >
      <div className="container mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/home" className="font-serif text-xl font-semibold text-foreground">
          MindVoice
        </Link>

        {variant === "dashboard" && userName && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground hidden sm:block">
              Hello, {userName}
            </span>
            <div className="w-10 h-10 rounded-full bg-sage-light flex items-center justify-center">
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
