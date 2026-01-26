"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { LucideIcon, ChevronRight } from "lucide-react";

interface DashboardCardProps {
  title: string;
  icon: LucideIcon;
  href: string;
  delay?: number;
}

export function DashboardCard({ title, icon: Icon, href, delay = 0 }: DashboardCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
    >
      <Link
        href={href}
        className="block p-6 bg-card border border-border rounded-2xl hover:border-sage/50 hover:shadow-soft transition-all group"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-sage/10 flex items-center justify-center">
              <Icon className="w-6 h-6 text-sage" />
            </div>
            <span className="font-medium text-lg text-foreground">{title}</span>
          </div>
          <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:text-foreground group-hover:translate-x-1 transition-all" />
        </div>
      </Link>
    </motion.div>
  );
}
