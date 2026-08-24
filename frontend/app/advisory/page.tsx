"use client";

import { useEffect, useState } from "react";
import { AdvisoryItem, RiskResult, getRisk } from "@/lib/api";

const formatCategoryName = (catStr?: string): string => {
  if (!catStr) return "General Safety Advice";
  const cleaned = catStr.toLowerCase().replace(/_/g, " ");
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
};

export default function AdvisoryPage() {
  const [activeUseCase, setActiveUseCase] = useState<"citizen" | "farmer" | "heat">("citizen");
  const [selectedCoords, setSelectedCoords] = useState<{ name: string; lat: number; lon: number }>({
    name: "Delhi / NCR",
    lat: 28.61,
    lon: 77.21,
  });
  const [riskData, setRiskData] = useState<RiskResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadAdvisories() {
      setLoading(true);
      setError(null);
      try {
        const res = await getRisk(selectedCoords.lat, selectedCoords.lon);
        setRiskData(res);
      } catch {
        setError("Unable to load advisory recommendations at the moment. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    loadAdvisories();
  }, [selectedCoords]);

  const presetLocations = [
    { name: "Delhi / NCR", lat: 28.61, lon: 77.21 },
    { name: "Uttar Pradesh (Agra)", lat: 27.18, lon: 78.01 },
    { name: "Rajasthan (Barmer)", lat: 27.2, lon: 70.9 },
    { name: "Mumbai", lat: 19.07, lon: 72.87 },
  ];

  // Filter advisory items by active use case
  const filteredAdvisories: AdvisoryItem[] =
    riskData?.advisory?.items?.filter((item) => {
      const uCase = (item.use_case || "").toLowerCase();
      if (activeUseCase === "farmer") return uCase.includes("farmer") || uCase.includes("agriculture");
      if (activeUseCase === "heat") return uCase.includes("heat") || uCase.includes("temperature");
      return uCase.includes("citizen") || uCase.includes("general") || uCase.includes("travel");
    }) || [];

  const getPriorityBadge = (priority: string) => {
    const p = (priority || "").toLowerCase();
    if (p === "high" || p === "critical" || p === "urgent") {
      return "bg-red-500/20 text-red-300 border-red-500/40";
    }
    if (p === "medium" || p === "moderate") {
      return "bg-amber-500/20 text-amber-300 border-amber-500/40";
    }
    return "bg-blue-500/20 text-blue-300 border-blue-500/40";
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header & Location Selector */}
      <div className="bg-slate-900/60 p-6 rounded-xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <span>📋</span> Weather Advisory Panel
          </h1>
          <p className="text-sm text-slate-400">
            Tailored safety precautions and operational guidance for specific personas.
          </p>
        </div>

        {/* Location selector */}
        <div className="flex flex-wrap gap-2">
          {presetLocations.map((loc) => (
            <button
              key={loc.name}
              onClick={() => setSelectedCoords(loc)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                selectedCoords.name === loc.name
                  ? "bg-blue-600 text-white border-blue-500 font-semibold"
                  : "bg-slate-950 text-slate-300 border-slate-800 hover:border-slate-700"
              }`}
            >
              {loc.name}
            </button>
          ))}
        </div>
      </div>

      {/* Use Case Tabs */}
      <div className="flex border-b border-slate-800 space-x-2">
        <button
          onClick={() => setActiveUseCase("citizen")}
          className={`px-5 py-3 text-sm font-semibold border-b-2 transition-colors ${
            activeUseCase === "citizen"
              ? "border-blue-500 text-blue-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          🏙️ Citizen & Travel Safety
        </button>

        <button
          onClick={() => setActiveUseCase("farmer")}
          className={`px-5 py-3 text-sm font-semibold border-b-2 transition-colors ${
            activeUseCase === "farmer"
              ? "border-emerald-500 text-emerald-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          🌾 Farmer & Agriculture
        </button>

        <button
          onClick={() => setActiveUseCase("heat")}
          className={`px-5 py-3 text-sm font-semibold border-b-2 transition-colors ${
            activeUseCase === "heat"
              ? "border-amber-500 text-amber-400"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          ☀️ Heat Wave & Health
        </button>
      </div>

      {/* Advisories Grid */}
      {loading ? (
        <div className="h-48 flex items-center justify-center bg-slate-900/40 rounded-xl border border-slate-800">
          <div className="text-slate-400 text-sm flex items-center space-x-2">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span>Generating recommendations for {selectedCoords.name}...</span>
          </div>
        </div>
      ) : error ? (
        <div className="p-4 bg-red-900/30 border border-red-800 rounded-xl text-red-300 text-sm">
          {error}
        </div>
      ) : (
        <div className="space-y-4">
          {riskData?.advisory?.summary && (
            <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 text-sm text-slate-200 flex items-center justify-between gap-4">
              <div>
                <span className="font-semibold text-blue-400">Overview: </span>
                {typeof riskData.advisory.summary === "object"
                  ? JSON.stringify(riskData.advisory.summary)
                  : String(riskData.advisory.summary)}
              </div>
              <span className="text-xs bg-slate-950 text-slate-300 px-3 py-1 rounded border border-slate-800 capitalize font-medium shrink-0">
                Risk Level: {riskData.level}
              </span>
            </div>
          )}

          {filteredAdvisories.length === 0 ? (
            <div className="p-8 text-center bg-slate-900/40 rounded-xl border border-slate-800 text-slate-400 text-sm">
              No severe weather advisories for this category under current conditions. All clear.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredAdvisories.map((item, idx) => (
                <div
                  key={idx}
                  className="bg-slate-900/80 p-5 rounded-xl border border-slate-800 hover:border-slate-700 transition-colors flex flex-col justify-between space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      {formatCategoryName(item.category || item.use_case)}
                    </span>
                    <span
                      className={`text-[10px] uppercase font-bold px-2.5 py-0.5 rounded border ${getPriorityBadge(
                        item.priority
                      )}`}
                    >
                      {item.priority ? `${item.priority} Priority` : "General Guidance"}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-base font-bold text-white">{item.title}</h3>
                    <p className="text-xs text-slate-300 mt-2 leading-relaxed">{item.description}</p>
                  </div>

                  <div className="text-[11px] text-slate-400 pt-2 border-t border-slate-800/60">
                    Source: Weather Intelligence Rule Engine
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
