"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { LucideIcon, ArrowUpRight } from "lucide-react";

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
      whileHover={{ y: -4 }}
    >
      <Link
        href={href}
        className="block p-6 bg-card border border-border rounded-2xl hover:border-sage hover:shadow-card transition-all group"
      >
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="w-14 h-14 rounded-2xl bg-sage-light flex items-center justify-center">
              <Icon className="w-7 h-7 text-sage" strokeWidth={1.5} />
            </div>
            <div className="w-10 h-10 rounded-full bg-sage-light flex items-center justify-center group-hover:bg-sage group-hover:text-white transition-all">
              <ArrowUpRight className="w-5 h-5 text-sage group-hover:text-white" />
            </div>
          </div>
          <span className="font-serif font-medium text-lg text-foreground">{title}</span>
        </div>
      </Link>
    </motion.div>
  );
}
