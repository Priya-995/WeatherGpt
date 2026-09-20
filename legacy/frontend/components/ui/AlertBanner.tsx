"use client";

import React from "react";
import Link from "next/link";
import { Alert } from "@/lib/api";
import { AlertTriangle, ArrowRight, BellRing } from "lucide-react";
import SeverityBadge, { normalizeSeverity } from "./SeverityBadge";

interface AlertBannerProps {
  alerts: Alert[];
  className?: string;
}

export default function AlertBanner({ alerts, className = "" }: AlertBannerProps) {
  if (!alerts || alerts.length === 0) return null;

  const topAlert = alerts[0];
  const norm = normalizeSeverity(topAlert.severity);

  // Exact pastel background + matching border tint
  const bannerStyles = {
    low: "bg-[#F0FDF4] border-[#15803D]/30 text-[#15803D]",
    moderate: "bg-[#FEF9C3] border-[#A16207]/30 text-[#A16207]",
    high: "bg-[#FFF8E6] border-[#D97706]/40 text-[#D97706]",
    critical: "bg-[#FFF0F0] border-[#ba1a1a]/40 text-[#ba1a1a]",
  };

  const currentStyle = bannerStyles[norm] || bannerStyles.critical;

  return (
    <div
      className={`p-4 rounded-xl border shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${currentStyle} ${className}`}
    >
      <div className="flex items-start space-x-3">
        <div className="p-2 bg-white/80 rounded-lg shrink-0 mt-0.5 sm:mt-0 shadow-xs">
          <BellRing className="w-5 h-5 animate-bounce" />
        </div>

        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider flex items-center gap-1 font-mono">
              Active Official Alert ({alerts.length})
            </span>
            <SeverityBadge severity={topAlert.severity} size="sm" />
          </div>
          <p className="text-body-sm font-medium leading-relaxed">
            <strong>{topAlert.affected_location}:</strong>{" "}
            {topAlert.instructions ? topAlert.instructions.slice(0, 140) : "Official warning active. Exercise caution."}
            {topAlert.instructions && topAlert.instructions.length > 140 ? "..." : ""}
          </p>
        </div>
      </div>

      <Link
        href="/alerts"
        className="bg-primary hover:bg-primary-container text-on-primary font-bold px-4 py-2.5 rounded-lg text-xs transition-all shrink-0 flex items-center space-x-1.5 shadow-sm group"
      >
        <span>View Alert Center</span>
        <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
      </Link>
    </div>
  );
}
