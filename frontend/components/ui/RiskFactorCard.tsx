"use client";

import React from "react";
import SeverityBadge from "./SeverityBadge";

interface RiskFactorCardProps {
  label: string;
  value: string | number;
  percentage: number;
  severity?: string;
  subtext?: string;
  className?: string;
}

export default function RiskFactorCard({
  label,
  value,
  percentage,
  severity = "low",
  subtext,
  className = "",
}: RiskFactorCardProps) {
  const normPct = Math.min(100, Math.max(0, percentage));

  const progressColor =
    normPct >= 70
      ? "bg-error"
      : normPct >= 40
      ? "bg-severity-moderate"
      : "bg-severity-low";

  return (
    <div
      className={`bg-surface-container-lowest p-4 rounded-xl border border-surface-container-high shadow-sm space-y-2.5 ${className}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-body-sm font-semibold text-on-surface">{label}</span>
        <SeverityBadge severity={severity} size="sm" />
      </div>

      <div className="flex items-baseline justify-between">
        <span className="text-headline-md font-bold text-primary">{value}</span>
        <span className="text-xs font-mono text-on-surface-variant font-medium">{normPct}% Index</span>
      </div>

      {/* Thin Progress Bar */}
      <div className="w-full h-1.5 bg-surface-container-high rounded-full overflow-hidden">
        <div
          className={`h-full ${progressColor} transition-all duration-500`}
          style={{ width: `${normPct}%` }}
        />
      </div>

      {subtext && (
        <p className="text-xs text-on-surface-variant pt-0.5 leading-relaxed">{subtext}</p>
      )}
    </div>
  );
}
