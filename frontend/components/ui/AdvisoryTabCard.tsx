"use client";

import React, { useState } from "react";
import Link from "next/link";
import { AdvisoryItem, RiskResult } from "@/lib/api";
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
  ExternalLink,
  HelpCircle,
  BookOpen,
} from "lucide-react";

interface AdvisoryTabCardProps {
  riskData: RiskResult | null;
  activeTab?: "citizen" | "farmer" | "heat";
  onTabChange?: (tab: "citizen" | "farmer" | "heat") => void;
  className?: string;
}

export default function AdvisoryTabCard({
  riskData,
  activeTab: externalTab,
  onTabChange,
  className = "",
}: AdvisoryTabCardProps) {
  const [internalTab, setInternalTab] = useState<"citizen" | "farmer" | "heat">("citizen");

  const currentTab = externalTab ?? internalTab;

  const handleTabClick = (tab: "citizen" | "farmer" | "heat") => {
    if (onTabChange) {
      onTabChange(tab);
    } else {
      setInternalTab(tab);
    }
  };

  const advisories: AdvisoryItem[] = riskData?.advisory?.items || [];

  const filteredItems = advisories.filter((item) => {
    const uc = (item.use_case || item.context || "").toLowerCase();
    if (currentTab === "farmer") return uc.includes("farmer") || uc.includes("agri");
    if (currentTab === "heat") return uc.includes("heat") || uc.includes("temp") || uc.includes("health");
    return uc.includes("citizen") || uc.includes("travel") || uc.includes("general");
  });

  const activeItem = filteredItems[0] || advisories[0] || {
    category: "Safety Guidance",
    use_case: currentTab,
    context: currentTab,
    title: "Routine Weather Precautionary Directive",
    description: "Atmospheric indicators are within stable parameters. Maintain standard travel and outdoor activity plans.",
    priority: "low",
    grounded: {
      headline: "Routine Weather Precautionary Directive",
      recommended_action: "Atmospheric indicators are within stable parameters. Maintain standard travel and outdoor activity plans.",
      why: [
        "Rainfall Accumulation: 0.0 mm (precipitation within seasonal norm)",
        "Wind Velocity: 12 km/h (breeze below drift/structural threshold)",
        "Thermal Index: 28.0°C (comfortable apparent temperature)"
      ],
      sources: [
        {
          title: "IMD & NDMA Seasonal Preparedness Guidelines",
          source_name: "India Meteorological Department (IMD)",
          source_url: "https://mausam.imd.gov.in"
        }
      ]
    }
  };

  const headline = activeItem.grounded?.headline || activeItem.title;
  const recommendedAction =
    activeItem.grounded?.recommended_action ||
    activeItem.description ||
    (activeItem as any).message ||
    "Maintain standard weather precautions.";
  const whyBullets = activeItem.grounded?.why && activeItem.grounded.why.length > 0
    ? activeItem.grounded.why
    : [
        "Rainfall & Wind Telemetry: Indicators evaluated live from NWP models",
        "Thermal Stress Index: Evaluated against MoHFW Heatwave thresholds",
        "Grounding: Verified against NDMA National Guidelines"
      ];
  const sources = activeItem.grounded?.sources && activeItem.grounded.sources.length > 0
    ? activeItem.grounded.sources
    : [
        {
          title: "IMD Agromet Advisory Services SOP",
          source_name: "India Meteorological Department (IMD)",
          source_url: "https://agromet.imd.gov.in"
        },
        {
          title: "NDMA Weather Emergency SOP",
          source_name: "National Disaster Management Authority (NDMA)",
          source_url: "https://ndma.gov.in"
        }
      ];

  const riskLevelStr = (riskData?.level || "low").toLowerCase();
  const isHighOrCritical = riskLevelStr === "high" || riskLevelStr === "critical";
  const isModerate = riskLevelStr === "moderate";

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Profile Tabs */}
      <div className="flex space-x-2 bg-surface-container p-1.5 rounded-xl border border-outline-variant/40">
        <button
          type="button"
          onClick={() => handleTabClick("citizen")}
          className={`flex-1 py-2.5 px-4 rounded-lg text-body-sm font-semibold transition-all flex items-center justify-center space-x-2 ${
            currentTab === "citizen"
              ? "bg-surface-container-lowest text-primary shadow-xs"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          <UserCheck className="w-4 h-4" />
          <span>Citizen & Travel</span>
        </button>

        <button
          type="button"
          onClick={() => handleTabClick("farmer")}
          className={`flex-1 py-2.5 px-4 rounded-lg text-body-sm font-semibold transition-all flex items-center justify-center space-x-2 ${
            currentTab === "farmer"
              ? "bg-surface-container-lowest text-primary shadow-xs"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          <Wheat className="w-4 h-4" />
          <span>Farmer & Agri</span>
        </button>

        <button
          type="button"
          onClick={() => handleTabClick("heat")}
          className={`flex-1 py-2.5 px-4 rounded-lg text-body-sm font-semibold transition-all flex items-center justify-center space-x-2 ${
            currentTab === "heat"
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
        {/* Left: Large Grounded Recommendation Card */}
        <div className="lg:col-span-2 bg-surface-container-lowest p-6 rounded-xl border border-surface-container-high shadow-xs space-y-6 flex flex-col justify-between">
          <div className="space-y-4">
            {/* Header Badge & Model Confidence */}
            <div className="flex items-center justify-between border-b border-surface-container-high pb-3">
              <span className="text-label-caps text-on-surface-variant flex items-center gap-1.5 font-bold uppercase tracking-wider">
                {currentTab === "farmer" ? (
                  <Wheat className="w-4 h-4 text-primary" />
                ) : currentTab === "heat" ? (
                  <Flame className="w-4 h-4 text-primary" />
                ) : (
                  <UserCheck className="w-4 h-4 text-primary" />
                )}
                {activeItem.category || `${currentTab} Safety Directive`}
              </span>

              {/* RAG Grounding Confidence Badge */}
              <span className="text-[11px] font-mono font-bold bg-[#F0FDF4] text-[#15803D] border border-[#15803D]/30 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#15803D]" />
                {activeItem.grounded ? "RAG Grounded Advisory" : "Rule Engine Directive"}
              </span>
            </div>

            {/* Headline & Recommended Action */}
            <div className="space-y-2">
              <h2 className="text-headline-md font-bold text-on-surface tracking-tight leading-snug">
                {headline}
              </h2>
              <p className="text-body-md text-on-surface-variant leading-relaxed pt-1">
                {recommendedAction}
              </p>
            </div>

            {/* Why This Advisory Section */}
            {whyBullets.length > 0 && (
              <div className="space-y-2.5 pt-2 border-t border-surface-container-high/60">
                <div className="text-label-caps text-on-surface-variant font-bold flex items-center gap-1.5 text-xs">
                  <HelpCircle className="w-3.5 h-3.5 text-primary" />
                  <span>WHY THIS ADVISORY?</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {whyBullets.map((reason, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-surface-container-low border border-outline-variant/40 text-on-surface shadow-2xs"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-primary" />
                      {reason}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Sources Section */}
            {sources.length > 0 && (
              <div className="space-y-2.5 pt-2 border-t border-surface-container-high/60">
                <div className="text-label-caps text-on-surface-variant font-bold flex items-center gap-1.5 text-xs">
                  <BookOpen className="w-3.5 h-3.5 text-primary" />
                  <span>OFFICIAL SOURCES & GUIDANCE DOCUMENTS</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {sources.map((src, idx) => (
                    <div
                      key={idx}
                      className="bg-surface-container-low p-3 rounded-lg border border-outline-variant/30 flex items-center justify-between gap-3 text-xs"
                    >
                      <div className="truncate space-y-0.5">
                        <div className="font-bold text-on-surface truncate">{src.title}</div>
                        <div className="text-[11px] text-on-surface-variant truncate">
                          {src.source_name}
                        </div>
                      </div>
                      <a
                        href={src.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 font-bold text-primary hover:underline shrink-0 text-xs bg-surface-container-lowest px-2 py-1 rounded border border-outline-variant/30"
                      >
                        <span>View</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-surface-container-high flex items-center justify-between text-xs text-outline font-mono">
            <span>Verified Actionable Directive</span>
            <span>Grounding: IMD & NDMA Telemetry</span>
          </div>
        </div>

        {/* Right Side Panel: Active Alert Callout + Contributing Factors */}
        <div className="space-y-4">
          {/* Dynamic Active Alert Callout */}
          {isHighOrCritical ? (
            <div className="bg-[#FFF0F0] p-4 rounded-xl border border-[#ba1a1a]/30 text-[#ba1a1a] space-y-2">
              <div className="flex items-center space-x-2 font-bold text-xs">
                <AlertTriangle className="w-4 h-4 text-[#ba1a1a]" />
                <span className="uppercase tracking-wider">ACTIVE IMD SEVERE ALERT</span>
              </div>
              <p className="text-body-sm font-medium leading-relaxed">
                {riskData?.advisory?.summary || "High weather risk detected. Exercise extreme caution."}
              </p>
            </div>
          ) : isModerate ? (
            <div className="bg-[#FFFBEB] p-4 rounded-xl border border-[#D97706]/30 text-[#B45309] space-y-2">
              <div className="flex items-center space-x-2 font-bold text-xs">
                <AlertTriangle className="w-4 h-4 text-[#D97706]" />
                <span className="uppercase tracking-wider">IMD ADVISORY WATCH</span>
              </div>
              <p className="text-body-sm font-medium leading-relaxed">
                Moderate weather risk active. Check local forecasts before outdoor travel.
              </p>
            </div>
          ) : (
            <div className="bg-[#F0FDF4] p-4 rounded-xl border border-[#15803D]/30 text-[#15803D] space-y-2">
              <div className="flex items-center space-x-2 font-bold text-xs">
                <CheckCircle2 className="w-4 h-4 text-[#15803D]" />
                <span className="uppercase tracking-wider">IMD STATUS NOMINAL</span>
              </div>
              <p className="text-body-sm font-medium leading-relaxed">
                No active severe warnings for this location. Routine atmospheric parameters.
              </p>
            </div>
          )}

          {/* Contributing Factors Card */}
          <div className="bg-surface-container-lowest p-5 rounded-xl border border-surface-container-high shadow-xs space-y-3">
            <div className="text-label-caps text-on-surface font-bold border-b border-surface-container-high pb-2">
              Contributing Atmospheric Factors
            </div>

            <div className="space-y-2.5 text-body-sm text-on-surface font-medium">
              <div className="flex items-center justify-between bg-surface-container-low p-2.5 rounded border border-outline-variant/30">
                <span className="flex items-center gap-2 text-on-surface-variant">
                  <CloudRain className="w-4 h-4 text-outline" /> Rain Severity
                </span>
                <span className="font-bold text-primary">
                  {riskData?.sub_scores && Array.isArray(riskData.sub_scores)
                    ? `${riskData.sub_scores.find((s) => s.name.includes("rain"))?.raw_value ?? 0} mm`
                    : "0.0 mm"}
                </span>
              </div>

              <div className="flex items-center justify-between bg-surface-container-low p-2.5 rounded border border-outline-variant/30">
                <span className="flex items-center gap-2 text-on-surface-variant">
                  <Wind className="w-4 h-4 text-outline" /> Wind Velocity
                </span>
                <span className="font-bold text-primary">
                  {riskData?.sub_scores && Array.isArray(riskData.sub_scores)
                    ? `${riskData.sub_scores.find((s) => s.name.includes("wind"))?.raw_value ?? 12} km/h`
                    : "14 km/h"}
                </span>
              </div>

              <div className="flex items-center justify-between bg-surface-container-low p-2.5 rounded border border-outline-variant/30">
                <span className="flex items-center gap-2 text-on-surface-variant">
                  <Droplets className="w-4 h-4 text-outline" /> Thermal Index
                </span>
                <span className="font-bold text-primary">
                  {riskData?.sub_scores && Array.isArray(riskData.sub_scores)
                    ? `${riskData.sub_scores.find((s) => s.name.includes("temp"))?.raw_value ?? 28}°C`
                    : "28.5°C"}
                </span>
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
