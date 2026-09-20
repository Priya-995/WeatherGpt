"use client";

import React from "react";
import { AdvisoryItem } from "@/lib/api";
import { UserCheck, Wheat, Flame, Building2, CheckCircle2 } from "lucide-react";
import SeverityBadge from "./SeverityBadge";

interface AdvisoryCardProps {
  item: AdvisoryItem;
  className?: string;
}

export default function AdvisoryCard({ item, className = "" }: AdvisoryCardProps) {
  const getPersonaIcon = (useCase?: string) => {
    const uc = (useCase || "").toLowerCase();
    if (uc.includes("farmer") || uc.includes("agri")) {
      return <Wheat className="w-4 h-4 text-slate-400" />;
    }
    if (uc.includes("heat") || uc.includes("temp")) {
      return <Flame className="w-4 h-4 text-slate-400" />;
    }
    if (uc.includes("govt") || uc.includes("disaster") || uc.includes("municipal")) {
      return <Building2 className="w-4 h-4 text-slate-400" />;
    }
    return <UserCheck className="w-4 h-4 text-slate-400" />;
  };

  const formatCategory = (cat?: string) => {
    if (!cat) return "General Safety Directive";
    return cat.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div
      className={`bg-slate-900 p-5 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all duration-200 shadow-md space-y-3.5 flex flex-col justify-between group ${className}`}
    >
      <div className="space-y-2.5">
        <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            {getPersonaIcon(item.use_case)}
            {formatCategory(item.category)}
          </span>
          {/* Priority Badge is the ONLY place severity colors appear */}
          <SeverityBadge severity={item.priority || "medium"} size="sm" labelOverride={`${item.priority || "Standard"} Priority`} />
        </div>

        <div>
          <h3 className="text-base font-bold text-white group-hover:text-slate-200 transition-colors">
            {item.title}
          </h3>
          <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed font-normal">
            {item.description}
          </p>
        </div>
      </div>

      <div className="text-[11px] text-slate-400 pt-2.5 border-t border-slate-800 flex items-center justify-between font-mono">
        <span className="flex items-center gap-1 text-slate-400">
          <CheckCircle2 className="w-3 h-3 text-slate-400" /> Action Directive
        </span>
        <span className="text-slate-500">WeatherGPT Engine</span>
      </div>
    </div>
  );
}
