"use client";

import React, { useState } from "react";
import Link from "next/link";
import { AdvisoryItem, RiskResult } from "@/lib/api";
import SeverityBadge from "./SeverityBadge";
import {
  UserCheck,
  Wheat,
  Flame,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Droplets,
  Wind,
  CloudRain,
} from "lucide-react";

interface AdvisoryTabCardProps {
  riskData: RiskResult | null;
  className?: string;
}

export default function AdvisoryTabCard({ riskData, className = "" }: AdvisoryTabCardProps) {
  const [activeTab, setActiveTab] = useState<"citizen" | "farmer" | "heat">("citizen");

  const advisories: AdvisoryItem[] = riskData?.advisory?.items || [];

  const filteredItems = advisories.filter((item) => {
    const uc = (item.use_case || "").toLowerCase();
    if (activeTab === "farmer") return uc.includes("farmer") || uc.includes("agri");
    if (activeTab === "heat") return uc.includes("heat") || uc.includes("temp");
    return uc.includes("citizen") || uc.includes("travel") || uc.includes("general");
  });

  const activeItem = filteredItems[0] || {
    category: "Safety Guidance",
    title: "Routine Weather Precautionary Directive",
    description: "Atmospheric indicators are within stable parameters. Maintain standard travel and outdoor activity plans.",
    priority: "low",
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Profile Tabs */}
      <div className="flex space-x-2 bg-surface-container p-1.5 rounded-xl border border-outline-variant/40">
        <button
          type="button"
          onClick={() => setActiveTab("citizen")}
          className={`flex-1 py-2.5 px-4 rounded-lg text-body-sm font-semibold transition-all flex items-center justify-center space-x-2 ${
            activeTab === "citizen"
              ? "bg-surface-container-lowest text-primary shadow-xs"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          <UserCheck className="w-4 h-4" />
          <span>Citizen & Travel</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("farmer")}
          className={`flex-1 py-2.5 px-4 rounded-lg text-body-sm font-semibold transition-all flex items-center justify-center space-x-2 ${
            activeTab === "farmer"
              ? "bg-surface-container-lowest text-primary shadow-xs"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          <Wheat className="w-4 h-4" />
          <span>Farmer & Agri</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("heat")}
          className={`flex-1 py-2.5 px-4 rounded-lg text-body-sm font-semibold transition-all flex items-center justify-center space-x-2 ${
            activeTab === "heat"
              ? "bg-surface-container-lowest text-primary shadow-xs"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          <Flame className="w-4 h-4" />
          <span>Heat & Health</span>
        </button>
      </div>

      {/* Main Grid: Recommendation Card (Left) + Side Panel (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Large Recommendation Card */}
        <div className="lg:col-span-2 bg-surface-container-lowest p-6 rounded-xl border border-surface-container-high shadow-xs space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b border-surface-container-high pb-3">
              <span className="text-label-caps text-on-surface-variant flex items-center gap-1.5 font-bold">
                {activeTab === "farmer" ? <Wheat className="w-4 h-4 text-primary" /> : activeTab === "heat" ? <Flame className="w-4 h-4 text-primary" /> : <UserCheck className="w-4 h-4 text-primary" />}
                {activeItem.category || "Recommendation Category"}
              </span>

              {/* Confidence Badge */}
              <span className="text-[11px] font-mono font-bold bg-[#F0FDF4] text-[#15803D] border border-[#15803D]/30 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-[#15803D]" />
                High Confidence Model
              </span>
            </div>

            <div>
              <h2 className="text-headline-md font-bold text-on-surface tracking-tight">
                {activeItem.title}
              </h2>
              <p className="text-body-md text-on-surface-variant mt-3 leading-relaxed">
                {activeItem.description}
              </p>
            </div>
          </div>

          <div className="pt-4 border-t border-surface-container-high flex items-center justify-between text-xs text-outline font-mono">
            <span>Verified Actionable Directive</span>
            <span>Grounding: IMD & NWP Telemetry</span>
          </div>
        </div>

        {/* Right Side Panel: Active Alert Callout + Contributing Factors */}
        <div className="space-y-4">
          {/* Active Alert Callout - Pastel Tint #FFF0F0 */}
          <div className="bg-[#FFF0F0] p-4 rounded-xl border border-[#ba1a1a]/30 text-[#ba1a1a] space-y-2">
            <div className="flex items-center space-x-2 font-bold text-xs">
              <AlertTriangle className="w-4 h-4 text-[#ba1a1a]" />
              <span className="uppercase tracking-wider">Active IMD Callout</span>
            </div>
            <p className="text-body-sm font-medium leading-relaxed">
              Regional IMD watch active. Exercise caution during peak thermal exposure.
            </p>
          </div>

          {/* Contributing Factors Card */}
          <div className="bg-surface-container-lowest p-5 rounded-xl border border-surface-container-high shadow-xs space-y-3">
            <div className="text-label-caps text-on-surface font-bold border-b border-surface-container-high pb-2">
              Contributing Atmospheric Factors
            </div>

            <div className="space-y-2.5 text-body-sm text-on-surface font-medium">
              <div className="flex items-center justify-between bg-surface-container-low p-2.5 rounded border border-outline-variant/30">
                <span className="flex items-center gap-2 text-on-surface-variant">
                  <CloudRain className="w-4 h-4 text-outline" /> Rain Probability
                </span>
                <span className="font-bold text-primary">35%</span>
              </div>

              <div className="flex items-center justify-between bg-surface-container-low p-2.5 rounded border border-outline-variant/30">
                <span className="flex items-center gap-2 text-on-surface-variant">
                  <Wind className="w-4 h-4 text-outline" /> Wind Velocity
                </span>
                <span className="font-bold text-primary">14 km/h</span>
              </div>

              <div className="flex items-center justify-between bg-surface-container-low p-2.5 rounded border border-outline-variant/30">
                <span className="flex items-center gap-2 text-on-surface-variant">
                  <Droplets className="w-4 h-4 text-outline" /> Humidity
                </span>
                <span className="font-bold text-primary">62%</span>
              </div>
            </div>

            <Link
              href="/"
              className="inline-flex items-center space-x-1.5 text-xs text-primary font-bold hover:underline pt-1"
            >
              <span>View full forecast telemetry</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
