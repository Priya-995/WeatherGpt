"use client";

import React from "react";
import { Alert } from "@/lib/api";
import SeverityBadge, { normalizeSeverity } from "./SeverityBadge";
import { Clock, MapPin, FileText } from "lucide-react";

interface AlertCardProps {
  alert: Alert;
  featured?: boolean;
  className?: string;
}

export default function AlertCard({ alert, featured = false, className = "" }: AlertCardProps) {
  const norm = normalizeSeverity(alert.severity);

  // Exact pastel tinted background per severity with matching thin border
  const severityCardStyles = {
    low: "bg-[#F0FDF4]/80 border-[#15803D]/30 text-[#15803D]",
    moderate: "bg-[#FEF9C3]/80 border-[#A16207]/30 text-[#A16207]",
    high: "bg-[#FFF8E6] border-[#D97706]/40 text-[#D97706]",
    critical: "bg-[#FFF0F0] border-[#ba1a1a]/40 text-[#ba1a1a]",
  };

  const instructionBoxStyles = {
    low: "bg-white/90 border-[#15803D]/40 text-[#15803D]",
    moderate: "bg-white/90 border-[#A16207]/40 text-[#A16207]",
    high: "bg-white/90 border-[#D97706]/40 text-[#D97706]",
    critical: "bg-white/90 border-[#ba1a1a]/40 text-[#ba1a1a]",
  };

  const cardStyle = severityCardStyles[norm] || severityCardStyles.low;
  const boxStyle = instructionBoxStyles[norm] || instructionBoxStyles.low;

  return (
    <div
      className={`p-6 rounded-xl border shadow-xs transition-all space-y-4 ${cardStyle} ${
        featured ? "md:col-span-2 shadow-sm" : ""
      } ${className}`}
    >
      {/* Top Header Row */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-current/20 pb-3">
        <div className="flex items-center space-x-2">
          <SeverityBadge severity={alert.severity} size="md" />
          <span className="text-xs font-semibold bg-white/90 text-on-surface px-2.5 py-0.5 rounded border border-outline-variant/40">
            {alert.alert_type ? alert.alert_type.replace(/_/g, " ").toUpperCase() : "WARNING"}
          </span>
        </div>

        <div className="flex items-center space-x-1.5 text-xs opacity-80 font-mono">
          <Clock className="w-3.5 h-3.5" />
          <span>Expires {new Date(alert.expiry_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="space-y-2">
        <div className="flex items-start space-x-2">
          <MapPin className="w-4 h-4 text-primary shrink-0 mt-1" />
          <h3 className="text-headline-sm font-semibold tracking-tight text-on-surface">
            {alert.affected_location}
          </h3>
        </div>

        {/* Highlighted Instruction Box */}
        {alert.instructions && (
          <div className={`p-3.5 rounded-lg border text-body-sm font-medium space-y-1 ${boxStyle}`}>
            <div className="text-label-caps flex items-center gap-1 font-bold">
              <FileText className="w-3.5 h-3.5" />
              Official Instruction Directive:
            </div>
            <p className="leading-relaxed">{alert.instructions}</p>
          </div>
        )}
      </div>

      {/* Footer Meta */}
      <div className="flex items-center justify-between text-xs opacity-80 pt-2 font-mono">
        <span>Source: {alert.source || "IMD Emergency Feed"}</span>
        <span>Issued: {new Date(alert.issue_time).toLocaleDateString()}</span>
      </div>
    </div>
  );
}
