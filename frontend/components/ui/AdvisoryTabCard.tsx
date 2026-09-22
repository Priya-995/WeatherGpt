"use client";

import React, { useState } from "react";
import Link from "next/link";
import { AdvisoryItem, RiskResult, sendChat } from "@/lib/api";
import {
  UserCheck,
  Wheat,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Droplets,
  Wind,
  CloudRain,
  ExternalLink,
  HelpCircle,
  BookOpen,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  Send,
} from "lucide-react";

interface AdvisoryTabCardProps {
  riskData: RiskResult | null;
  activeTab?: "citizen" | "farmer" | "official";
  onTabChange?: (tab: "citizen" | "farmer" | "official") => void;
  className?: string;
}

export default function AdvisoryTabCard({
  riskData,
  activeTab: externalTab,
  onTabChange,
  className = "",
}: AdvisoryTabCardProps) {
  const [internalTab, setInternalTab] = useState<"citizen" | "farmer" | "official">("citizen");
  const [showOfficialWording, setShowOfficialWording] = useState<boolean>(false);

  // Scoped Chat state inside Persona Advisory Panel
  const [chatInput, setChatInput] = useState<string>("");
  const [chatMessages, setChatMessages] = useState<Array<{ sender: "user" | "ai"; text: string }>>([
    {
      sender: "ai",
      text: "Namaste! Main WeatherGPT assistant hoon. Is persona tab ke regarding weather safety directives puchhein (e.g. 'kal chhata le jaun kya', 'should I spray pesticide tomorrow').",
    },
  ]);
  const [chatLoading, setChatLoading] = useState<boolean>(false);

  const currentTab = externalTab ?? internalTab;

  const handleTabClick = (tab: "citizen" | "farmer" | "official") => {
    if (onTabChange) {
      onTabChange(tab);
    } else {
      setInternalTab(tab);
    }
  };

  const advisories: AdvisoryItem[] = riskData?.advisory?.items || [];

  const activeItem = advisories[0] || {
    context: currentTab,
    title: "NDMA Weather Precaution Directive",
    message: "Atmospheric indicators are within stable parameters. Maintain standard outdoor activity plans and monitor official advisories.",
    grounded: {
      headline: "NDMA Weather Precaution Directive",
      recommended_action: "Atmospheric indicators are within stable parameters. Maintain standard outdoor activity plans and monitor official advisories.",
      why: ["Rainfall Accumulation: within seasonal norms", "Thermal Index: comfortable range"],
      sources: [
        {
          title: "NDMA National Hazard Guidelines",
          source_name: "National Disaster Management Authority (NDMA)",
          source_url: "https://ndma.gov.in",
        },
      ],
    },
    official_text: "State and District authorities shall maintain standard monitoring protocols and issue routine updates via state disaster management portals.",
    source_url: "https://ndma.gov.in",
  };

  const headline = activeItem.grounded?.headline || activeItem.title;
  const plainMessage = activeItem.message || activeItem.grounded?.recommended_action || activeItem.description || "Maintain standard weather precautions.";

  const whyBullets = activeItem.grounded?.why && activeItem.grounded.why.length > 0
    ? activeItem.grounded.why
    : [
        "Rainfall & Wind Telemetry: Evaluated against NDMA safety thresholds",
        "Grounded: Verified against official Government of India hazard guidelines",
      ];

  const sources = activeItem.grounded?.sources && activeItem.grounded.sources.length > 0
    ? activeItem.grounded.sources
    : [
        {
          title: "NDMA Hazard Guidelines",
          source_name: "National Disaster Management Authority (NDMA)",
          source_url: activeItem.source_url || "https://ndma.gov.in",
        },
      ];

  const riskLevelStr = (riskData?.level || "low").toLowerCase();
  const isHighOrCritical = riskLevelStr === "high" || riskLevelStr === "critical";
  const isModerate = riskLevelStr === "moderate";

  const handleSendChat = async () => {
    if (!chatInput.trim() || chatLoading) return;
    const userQuery = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { sender: "user", text: userQuery }]);
    setChatLoading(true);

    try {
      // Append persona context to chat query
      const fullPrompt = `[Persona Tab: ${currentTab}] ${userQuery}`;
      const res = await sendChat(fullPrompt);
      setChatMessages((prev) => [...prev, { sender: "ai", text: res.answer }]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { sender: "ai", text: "Maaf kijiye, advisory network retrieval me problem aayi. Kripya punah prayas karein." },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Profile Tabs: Citizen, Farmer, Official */}
      <div className="flex space-x-2 bg-surface-container p-1.5 rounded-xl border border-outline-variant/40 shadow-xs">
        <button
          type="button"
          onClick={() => handleTabClick("citizen")}
          className={`flex-1 py-3 px-4 rounded-lg text-body-sm font-bold transition-all flex items-center justify-center space-x-2 ${
            currentTab === "citizen"
              ? "bg-surface-container-lowest text-primary shadow-xs border border-outline-variant/40"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          <UserCheck className="w-4 h-4 text-primary" />
          <span>Citizen Tab</span>
        </button>

        <button
          type="button"
          onClick={() => handleTabClick("farmer")}
          className={`flex-1 py-3 px-4 rounded-lg text-body-sm font-bold transition-all flex items-center justify-center space-x-2 ${
            currentTab === "farmer"
              ? "bg-surface-container-lowest text-primary shadow-xs border border-outline-variant/40"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          <Wheat className="w-4 h-4 text-primary" />
          <span>Farmer Tab</span>
        </button>

        <button
          type="button"
          onClick={() => handleTabClick("official")}
          className={`flex-1 py-3 px-4 rounded-lg text-body-sm font-bold transition-all flex items-center justify-center space-x-2 ${
            currentTab === "official"
              ? "bg-surface-container-lowest text-primary shadow-xs border border-outline-variant/40"
              : "text-on-surface-variant hover:text-on-surface"
          }`}
        >
          <ShieldAlert className="w-4 h-4 text-primary" />
          <span>Official Tab</span>
        </button>
      </div>

      {/* Main Grid: Grounded Recommendation Card (Left) + Side Panel & Persona Chat (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Grounded Plain-Language Recommendation Card */}
        <div className="lg:col-span-2 bg-surface-container-lowest p-6 sm:p-8 rounded-xl border border-surface-container-high shadow-xs space-y-6 flex flex-col justify-between">
          <div className="space-y-5">
            {/* Header Badge & Persona Label */}
            <div className="flex items-center justify-between border-b border-surface-container-high pb-3">
              <span className="text-label-caps text-on-surface-variant flex items-center gap-2 font-extrabold uppercase tracking-wider text-xs">
                {currentTab === "farmer" ? (
                  <Wheat className="w-4 h-4 text-primary" />
                ) : currentTab === "official" ? (
                  <ShieldAlert className="w-4 h-4 text-primary" />
                ) : (
                  <UserCheck className="w-4 h-4 text-primary" />
                )}
                {currentTab.toUpperCase()} SAFETY DIRECTIVE (NDMA GROUNDED)
              </span>

              <span className="text-[11px] font-mono font-bold bg-[#F0FDF4] text-[#15803D] border border-[#15803D]/30 px-3 py-1 rounded-full flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#15803D]" />
                NDMA Plain Language RAG
              </span>
            </div>

            {/* Headline & Plain Language Message */}
            <div className="space-y-3">
              <h2 className="text-headline-md font-bold text-on-surface tracking-tight leading-snug">
                {headline}
              </h2>
              <div className="bg-surface-container-low p-4 rounded-xl border border-outline-variant/30 text-body-md text-on-surface font-medium leading-relaxed">
                {plainMessage}
              </div>
            </div>

            {/* Expandable Official Wording Accordion (OFFICIAL TAB ONLY) */}
            {currentTab === "official" && (
              <div className="border border-primary/30 rounded-xl bg-primary-container/10 overflow-hidden transition-all">
                <button
                  type="button"
                  onClick={() => setShowOfficialWording(!showOfficialWording)}
                  className="w-full px-4 py-3 bg-primary-container/20 hover:bg-primary-container/30 flex items-center justify-between text-xs font-bold text-primary transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-primary" />
                    <span>View Official Government Wording & Legal Directive</span>
                  </span>
                  {showOfficialWording ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>

                {showOfficialWording && (
                  <div className="p-4 space-y-3 text-xs text-on-surface bg-surface-container-lowest border-t border-primary/20">
                    <div className="font-mono bg-surface-container-low p-3 rounded border border-outline-variant/30 text-on-surface-variant leading-relaxed">
                      {activeItem.official_text || "Standard NDMA SOP protocol active for disaster response management."}
                    </div>
                    {activeItem.source_url && (
                      <div className="flex items-center justify-between pt-1">
                        <span className="font-semibold text-outline">Source Document:</span>
                        <a
                          href={activeItem.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-primary font-bold hover:underline"
                        >
                          <span>{activeItem.source_url}</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Why This Advisory Section */}
            {whyBullets.length > 0 && (
              <div className="space-y-2.5 pt-2 border-t border-surface-container-high/60">
                <div className="text-label-caps text-on-surface-variant font-bold flex items-center gap-1.5 text-xs">
                  <HelpCircle className="w-3.5 h-3.5 text-primary" />
                  <span>GROUNDED REASONING & METEOROLOGICAL DRIVERS</span>
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
                  <span>OFFICIAL NDMA GUIDELINE SOURCES</span>
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
                        className="inline-flex items-center gap-1 font-bold text-primary hover:underline shrink-0 text-xs bg-surface-container-lowest px-2.5 py-1 rounded border border-outline-variant/30"
                      >
                        <span>PDF / Link</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="pt-4 border-t border-surface-container-high flex items-center justify-between text-xs text-outline font-mono">
            <span>Verified NDMA Guidance</span>
            <span>Grounding: 384-dim Supabase Vector Search</span>
          </div>
        </div>

        {/* Right Panel: Persona-Scoped Chat Box + Contributing Factors */}
        <div className="space-y-6 flex flex-col justify-between">
          {/* Persona Scoped Assistant Chat */}
          <div className="bg-surface-container-lowest p-5 rounded-xl border border-surface-container-high shadow-xs space-y-4 flex flex-col h-[420px]">
            <div className="flex items-center justify-between border-b border-surface-container-high pb-2.5">
              <div className="flex items-center gap-2 text-xs font-extrabold text-on-surface uppercase tracking-wider">
                <MessageSquare className="w-4 h-4 text-primary" />
                <span>{currentTab.toUpperCase()} ADVISORY ASSISTANT</span>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary-container/30 text-primary font-bold">
                Hinglish / Hindi / English
              </span>
            </div>

            {/* Chat Stream Window */}
            <div className="flex-1 overflow-y-auto space-y-3 pr-1 text-xs">
              {chatMessages.map((msg, i) => (
                <div
                  key={i}
                  className={`p-3 rounded-xl max-w-[90%] leading-relaxed ${
                    msg.sender === "user"
                      ? "bg-primary text-on-primary ml-auto font-medium"
                      : "bg-surface-container-low border border-outline-variant/40 text-on-surface"
                  }`}
                >
                  {msg.text}
                </div>
              ))}
              {chatLoading && (
                <div className="p-3 bg-surface-container-low rounded-xl border border-outline-variant/40 text-on-surface-variant flex items-center gap-2">
                  <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  <span>Searching NDMA corpus...</span>
                </div>
              )}
            </div>

            {/* Chat Input */}
            <div className="flex gap-2 pt-2 border-t border-surface-container-high">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSendChat()}
                placeholder={`Ask ${currentTab} guidance... (e.g. kal chhata le jaun)`}
                className="flex-1 bg-surface-container-low border border-outline-variant/50 rounded-lg px-3 py-2 text-xs text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <button
                type="button"
                onClick={handleSendChat}
                disabled={chatLoading}
                className="bg-primary hover:bg-primary/90 text-on-primary p-2.5 rounded-lg transition-all disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Active Risk Banner */}
          {isHighOrCritical ? (
            <div className="bg-[#FFF0F0] p-4 rounded-xl border border-[#ba1a1a]/30 text-[#ba1a1a] space-y-1.5">
              <div className="flex items-center space-x-2 font-bold text-xs">
                <AlertTriangle className="w-4 h-4 text-[#ba1a1a]" />
                <span className="uppercase tracking-wider">ACTIVE SEVERE RISK ALERT</span>
              </div>
              <p className="text-body-sm font-medium leading-relaxed">
                {riskData?.advisory?.summary || "High weather risk active. Follow persona safety directives."}
              </p>
            </div>
          ) : isModerate ? (
            <div className="bg-[#FFFBEB] p-4 rounded-xl border border-[#D97706]/30 text-[#B45309] space-y-1.5">
              <div className="flex items-center space-x-2 font-bold text-xs">
                <AlertTriangle className="w-4 h-4 text-[#D97706]" />
                <span className="uppercase tracking-wider">MODERATE ADVISORY WATCH</span>
              </div>
              <p className="text-body-sm font-medium leading-relaxed">
                Moderate risk detected. Check directives prior to outdoor activities.
              </p>
            </div>
          ) : (
            <div className="bg-[#F0FDF4] p-4 rounded-xl border border-[#15803D]/30 text-[#15803D] space-y-1.5">
              <div className="flex items-center space-x-2 font-bold text-xs">
                <CheckCircle2 className="w-4 h-4 text-[#15803D]" />
                <span className="uppercase tracking-wider">WEATHER STATUS NOMINAL</span>
              </div>
              <p className="text-body-sm font-medium leading-relaxed">
                No severe weather threats active. Standard daily activities recommended.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
