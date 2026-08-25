"use client";

import React from "react";
import { Info, AlertTriangle, AlertCircle, Flame } from "lucide-react";

export type SeverityLevel = "low" | "moderate" | "medium" | "high" | "severe" | "critical" | string;

interface SeverityBadgeProps {
  severity: SeverityLevel;
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
  className?: string;
  labelOverride?: string;
}

export function normalizeSeverity(severity: string): "low" | "moderate" | "high" | "critical" {
  const s = (severity || "").toLowerCase().trim();
  if (s === "critical" || s === "severe" || s === "red" || s === "extreme" || s === "urgent") {
    return "critical";
  }
  if (s === "high" || s === "orange" || s === "watch") {
    return "high";
  }
  if (s === "moderate" || s === "medium" || s === "yellow" || s === "advisory") {
    return "moderate";
  }
  return "low";
}

export default function SeverityBadge({
  severity,
  size = "md",
  showIcon = true,
  className = "",
  labelOverride,
}: SeverityBadgeProps) {
  const level = normalizeSeverity(severity);

  const sizeStyles = {
    sm: "px-2 py-0.5 text-[11px] font-semibold gap-1",
    md: "px-2.5 py-1 text-xs font-bold gap-1.5",
    lg: "px-3 py-1.5 text-sm font-extrabold gap-2",
  };

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16,
  };

  // Exact pastel tint specifications
  const config = {
    low: {
      label: "LOW RISK",
      bg: "bg-[#F0FDF4]/80 text-[#15803D] border-[#15803D]/40",
      icon: Info,
    },
    moderate: {
      label: "MODERATE ADVISORY",
      bg: "bg-[#FEF9C3]/80 text-[#A16207] border-[#A16207]/40",
      icon: AlertCircle,
    },
    high: {
      label: "HIGH WATCH",
      bg: "bg-[#FFF8E6] text-[#D97706] border-[#D97706]/40",
      icon: AlertTriangle,
    },
    critical: {
      label: "CRITICAL WARNING",
      bg: "bg-[#FFF0F0] text-[#ba1a1a] border-[#ba1a1a]/40",
      icon: Flame,
    },
  };

  const current = config[level] || config.low;
  const IconComponent = current.icon;
  const label = labelOverride || current.label;

  return (
    <span
      className={`inline-flex items-center rounded-full border uppercase tracking-wider transition-all ${sizeStyles[size]} ${current.bg} ${className}`}
    >
      {showIcon && <IconComponent size={iconSizes[size]} className="shrink-0" />}
      <span>{label}</span>
    </span>
  );
}
