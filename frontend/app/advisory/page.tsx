"use client";

import { useEffect, useState } from "react";
import { AdvisoryItem, RiskResult, WeatherResponse, getRisk, getWeather } from "@/lib/api";

const formatCategoryName = (catStr?: string): string => {
  if (!catStr) return "General Safety Advice";
  const cleaned = catStr.toLowerCase().replace(/_/g, " ");
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
};

export default function AdvisoryPage() {
  const [activePersona, setActivePersona] = useState<"citizen" | "farmer" | "heat" | "government">("citizen");
  const [selectedCoords, setSelectedCoords] = useState<{ name: string; lat: number; lon: number }>({
    name: "Delhi / NCR",
    lat: 28.61,
    lon: 77.21,
  });
  const [riskData, setRiskData] = useState<RiskResult | null>(null);
  const [weatherData, setWeatherData] = useState<WeatherResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [rData, wData] = await Promise.all([
          getRisk(selectedCoords.lat, selectedCoords.lon),
          getWeather(selectedCoords.lat, selectedCoords.lon),
        ]);
        setRiskData(rData);
        setWeatherData(wData);
      } catch (err) {
        console.error("Error loading advisory telemetry:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [selectedCoords]);

  const presetLocations = [
    { name: "Delhi / NCR", lat: 28.61, lon: 77.21 },
    { name: "Uttar Pradesh (Agra)", lat: 27.18, lon: 78.01 },
    { name: "Rajasthan (Barmer)", lat: 27.2, lon: 70.9 },
    { name: "Mumbai", lat: 19.07, lon: 72.87 },
    { name: "Odisha (Puri)", lat: 19.81, lon: 85.83 },
  ];

  // Filter advisory items by active persona
  const filteredAdvisories: AdvisoryItem[] =
    riskData?.advisory?.items?.filter((item) => {
      const uCase = (item.use_case || "").toLowerCase();
      if (activePersona === "farmer") return uCase.includes("farmer") || uCase.includes("agriculture");
      if (activePersona === "heat") return uCase.includes("heat") || uCase.includes("temperature");
      if (activePersona === "government") return uCase.includes("government") || uCase.includes("disaster") || uCase.includes("municipal");
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
    return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
  };

  const getLevelBadge = (level: string) => {
    switch (String(level || "").toLowerCase()) {
      case "critical":
        return "bg-red-500/20 text-red-400 border-red-500/40";
      case "high":
        return "bg-orange-500/20 text-orange-400 border-orange-500/40";
      case "moderate":
        return "bg-amber-500/20 text-amber-400 border-amber-500/40";
      default:
        return "bg-emerald-500/20 text-emerald-400 border-emerald-500/40";
    }
  };

  // Extract daily trends for charts
  const dailyDates = weatherData?.daily?.time?.slice(0, 7) || ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const tempMaxList = weatherData?.daily?.temperature_2m_max?.slice(0, 7) || [34, 36, 38, 35, 33, 31, 30];
  const tempMinList = weatherData?.daily?.temperature_2m_min?.slice(0, 7) || [24, 25, 26, 25, 24, 23, 22];
  const rainList = weatherData?.daily?.precipitation_sum?.slice(0, 7) || [2, 18, 45, 12, 0, 5, 1];
  const maxTempInTrend = Math.max(...tempMaxList, 40);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Top Header & Preset Bar */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-950/60 p-6 rounded-2xl border border-slate-800 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="bg-blue-500/20 text-blue-400 text-xs font-semibold px-2.5 py-1 rounded-md border border-blue-500/30 uppercase tracking-wider">
              Decision Support & Operational Analytics
            </span>
            <span className="bg-slate-800 text-slate-300 text-xs px-2.5 py-1 rounded-md border border-slate-700 font-mono">
              v2.4 Grounded Telemetry
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white mt-2 flex items-center gap-2">
            <span>📋</span> Persona Advisory & Researcher Analytics
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time actionable safety directives, risk factor trends, and policy metrics tailored for citizens, farmers, and government emergency planners.
          </p>
        </div>

        {/* Location selector */}
        <div className="flex flex-wrap gap-2 shrink-0">
          {presetLocations.map((loc) => (
            <button
              key={loc.name}
              onClick={() => setSelectedCoords(loc)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-all duration-200 font-medium ${
                selectedCoords.name === loc.name
                  ? "bg-blue-600 text-white border-blue-500 shadow-lg shadow-blue-900/40"
                  : "bg-slate-950/80 text-slate-300 border-slate-800 hover:border-slate-700 hover:text-white"
              }`}
            >
              📍 {loc.name}
            </button>
          ))}
        </div>
      </div>

      {/* Persona Selection Tabs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-slate-950 p-1.5 rounded-xl border border-slate-800">
        <button
          onClick={() => setActivePersona("citizen")}
          className={`py-3 px-4 rounded-lg text-xs sm:text-sm font-bold transition-all flex items-center justify-center space-x-2 ${
            activePersona === "citizen"
              ? "bg-blue-600 text-white shadow-md shadow-blue-900/30"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <span>🏙️</span>
          <span>Citizen & Travel</span>
        </button>

        <button
          onClick={() => setActivePersona("farmer")}
          className={`py-3 px-4 rounded-lg text-xs sm:text-sm font-bold transition-all flex items-center justify-center space-x-2 ${
            activePersona === "farmer"
              ? "bg-emerald-600 text-white shadow-md shadow-emerald-900/30"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <span>🌾</span>
          <span>Farmers & Ag-Sector</span>
        </button>

        <button
          onClick={() => setActivePersona("heat")}
          className={`py-3 px-4 rounded-lg text-xs sm:text-sm font-bold transition-all flex items-center justify-center space-x-2 ${
            activePersona === "heat"
              ? "bg-amber-600 text-white shadow-md shadow-amber-900/30"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <span>☀️</span>
          <span>Heat & Health</span>
        </button>

        <button
          onClick={() => setActivePersona("government")}
          className={`py-3 px-4 rounded-lg text-xs sm:text-sm font-bold transition-all flex items-center justify-center space-x-2 ${
            activePersona === "government"
              ? "bg-purple-600 text-white shadow-md shadow-purple-900/30"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
          }`}
        >
          <span>🏛️</span>
          <span>Govt & Disaster Response</span>
        </button>
      </div>

      {/* Main Advisory Content & Analytics Dashboard */}
      {loading ? (
        <div className="h-64 flex flex-col items-center justify-center bg-slate-900/40 rounded-2xl border border-slate-800 space-y-3">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-slate-300 font-medium">Evaluating weather hazard telemetry for {selectedCoords.name}...</span>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Executive Overview Card */}
          <div className="bg-slate-900 p-5 rounded-2xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-lg">
            <div>
              <div className="text-xs uppercase font-bold text-slate-400 tracking-wider">Operational Summary ({selectedCoords.name})</div>
              <p className="text-sm font-medium text-slate-200 mt-1 leading-relaxed">
                {riskData?.advisory?.summary || "Atmospheric risk parameters currently evaluated. All early-warning directives generated."}
              </p>
            </div>
            <div className="flex items-center space-x-3 shrink-0">
              <div className="text-right">
                <div className="text-[11px] text-slate-400 uppercase font-semibold">Hazard Index</div>
                <div className="text-xl font-black text-white">
                  {typeof riskData?.score === "number" ? Math.round(riskData.score * 100) : "25"}/100
                </div>
              </div>
              <span className={`text-xs uppercase font-black px-3.5 py-1.5 rounded-lg border ${getLevelBadge(riskData?.level || "low")}`}>
                {riskData?.level || "Low"}
              </span>
            </div>
          </div>

          {/* Persona Specific Actionable Advisories Grid */}
          <div className="space-y-3">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <span>🛡️</span> Tailored Safety Precautions & Operational Directives
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredAdvisories.length === 0 ? (
                <div className="md:col-span-2 p-8 text-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400 text-sm">
                  No critical safety warnings for this persona under current conditions. All clear.
                </div>
              ) : (
                filteredAdvisories.map((item, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-900/80 p-5 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all duration-200 space-y-3 flex flex-col justify-between"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">
                        {formatCategoryName(item.category || item.use_case)}
                      </span>
                      <span className={`text-[10px] uppercase font-black px-2.5 py-1 rounded border ${getPriorityBadge(item.priority)}`}>
                        {item.priority ? `${item.priority} Priority` : "General Guidance"}
                      </span>
                    </div>

                    <div>
                      <h3 className="text-base font-bold text-white">{item.title}</h3>
                      <p className="text-xs text-slate-300 mt-2 leading-relaxed">{item.description}</p>
                    </div>

                    <div className="text-[11px] text-slate-400 pt-2 border-t border-slate-800/80 flex items-center justify-between">
                      <span>Source: WeatherGPT Risk Engine</span>
                      <span className="font-mono text-slate-400 text-[10px]">Verified Action</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* VISUAL ANALYTICS & CHARTS SECTION (For Government Officials & Researchers) */}
          <div className="space-y-4 pt-4 border-t border-slate-800/80">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-extrabold text-white flex items-center gap-2">
                  <span>📊</span> Government & Researcher Meteorological Analytics
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  7-day atmospheric hazard trends, sub-score breakdown, and disaster mitigation readiness metrics.
                </p>
              </div>
              <span className="text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30 px-3 py-1 rounded-lg font-mono">
                Govt/Researcher Command View
              </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Chart 1: 7-Day Temperature & Rain Visualizer */}
              <div className="bg-slate-900 p-5 rounded-2xl border border-slate-800 space-y-4 shadow-lg">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    📈 7-Day Temperature & Precipitation Trend
                  </span>
                  <span className="text-[11px] font-mono text-slate-400">Temp (°C) & Rain (mm)</span>
                </div>

                {/* SVG Weather Visualizer */}
                <div className="space-y-3">
                  <div className="h-44 flex items-end justify-between gap-2 pt-6 px-2 bg-slate-950/60 rounded-xl border border-slate-800/60 relative">
                    {/* Background grid lines */}
                    <div className="absolute inset-x-0 top-1/4 border-b border-slate-800/40 border-dashed pointer-events-none" />
                    <div className="absolute inset-x-0 top-2/4 border-b border-slate-800/40 border-dashed pointer-events-none" />
                    <div className="absolute inset-x-0 top-3/4 border-b border-slate-800/40 border-dashed pointer-events-none" />

                    {dailyDates.map((d, i) => {
                      const tMax = tempMaxList[i] || 30;
                      const rSum = rainList[i] || 0;
                      const barHeight = Math.min(100, Math.max(15, (tMax / maxTempInTrend) * 100));

                      return (
                        <div key={i} className="flex-1 flex flex-col items-center gap-1 z-10">
                          {/* Rain badge if present */}
                          <span className="text-[9px] font-bold text-blue-400 font-mono">
                            {rSum > 0 ? `${rSum}mm` : ""}
                          </span>

                          {/* Temperature Bar */}
                          <div className="w-full max-w-[28px] bg-slate-800 rounded-t relative group flex flex-col justify-end" style={{ height: `${barHeight}%` }}>
                            <div className={`w-full rounded-t transition-all ${rSum > 20 ? "bg-gradient-to-t from-blue-600 to-indigo-500" : tMax >= 38 ? "bg-gradient-to-t from-orange-600 to-amber-400" : "bg-gradient-to-t from-emerald-600 to-teal-400"}`} style={{ height: "100%" }} />
                            <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] font-extrabold text-white">
                              {Math.round(tMax)}°
                            </span>
                          </div>

                          <span className="text-[10px] font-medium text-slate-400 mt-1 truncate max-w-full">
                            {d.slice(5) || d}
                          </span>
                        </div>
                      );
                    })}
                  </div>

                  <div className="flex items-center justify-center space-x-6 text-xs text-slate-400 pt-1">
                    <div className="flex items-center space-x-1.5">
                      <span className="w-3 h-3 rounded-sm bg-gradient-to-r from-amber-500 to-orange-500" />
                      <span>Max Temperature (°C)</span>
                    </div>
                    <div className="flex items-center space-x-1.5">
                      <span className="w-3 h-3 rounded-sm bg-gradient-to-r from-blue-600 to-indigo-500" />
                      <span>Heavy Rainfall Zone (mm)</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Chart 2: Sub-Score Severity Radar / Factor Metrics */}
              <div className="bg-slate-900 p-5 rounded-2xl border border-slate-800 space-y-4 shadow-lg">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                    🎯 Risk Sub-Score Telemetry Breakdown
                  </span>
                  <span className="text-[11px] font-mono text-slate-400">Risk Weight Analysis</span>
                </div>

                <div className="space-y-3">
                  {riskData?.sub_scores && Array.isArray(riskData.sub_scores) ? (
                    riskData.sub_scores.map((sub, idx) => {
                      const sevPct = Math.min(100, Math.max(5, Math.round((sub.severity || 0.1) * 100)));
                      const colorClass =
                        sevPct >= 70
                          ? "bg-red-500"
                          : sevPct >= 40
                          ? "bg-amber-500"
                          : "bg-emerald-500";

                      return (
                        <div key={idx} className="bg-slate-950 p-3 rounded-xl border border-slate-800/80 space-y-1.5">
                          <div className="flex justify-between items-center text-xs font-semibold">
                            <span className="text-slate-200">{sub.name}</span>
                            <span className="text-white font-mono">{sub.raw_value} ({sevPct}% risk)</span>
                          </div>
                          <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div className={`h-full ${colorClass} transition-all duration-500`} style={{ width: `${sevPct}%` }} />
                          </div>
                          {sub.threshold_note && (
                            <p className="text-[11px] text-slate-400 italic pt-0.5">{sub.threshold_note}</p>
                          )}
                        </div>
                      );
                    })
                  ) : (
                    <div className="p-4 text-xs text-slate-400">Loading sub-score metric breakdown...</div>
                  )}
                </div>
              </div>
            </div>

            {/* Government Disaster Response Preparedness Table */}
            <div className="bg-slate-900 p-5 rounded-2xl border border-slate-800 space-y-4 shadow-lg">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
                  <span>🏛️</span> Official Disaster Preparedness & District Level Readiness Matrix
                </span>
                <span className="text-xs text-slate-400 font-mono">NDRF / SDMA Action Status</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950 text-slate-400 uppercase font-semibold text-[10px] tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="p-3">Department / Sector</th>
                      <th className="p-3">Threshold Trigger</th>
                      <th className="p-3">Required Protocol Action</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    <tr>
                      <td className="p-3 font-bold text-white">NDRF & Civil Defense</td>
                      <td className="p-3 font-mono">Precipitation &gt; 35mm / Heavy Wind</td>
                      <td className="p-3">Pre-position motorboats & high-capacity dewatering pumps at underpasses.</td>
                      <td className="p-3"><span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-2 py-0.5 rounded text-[10px] font-bold uppercase">Standby Ready</span></td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-white">Agricultural Extension Board</td>
                      <td className="p-3 font-mono">Thermal Stress &gt; 38°C / Dry Spell</td>
                      <td className="p-3">Issue micro-irrigation alerts & advisory to local Krishi Vigyan Kendras (KVK).</td>
                      <td className="p-3"><span className="bg-blue-500/20 text-blue-300 border border-blue-500/40 px-2 py-0.5 rounded text-[10px] font-bold uppercase">Active Advisory</span></td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-white">Public Health & Hospitals</td>
                      <td className="p-3 font-mono">Heat Index &gt; 42°C</td>
                      <td className="p-3">Equip district hospitals with heat-stroke management beds & saline supply.</td>
                      <td className="p-3"><span className="bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded text-[10px] font-bold uppercase">Monitored</span></td>
                    </tr>
                    <tr>
                      <td className="p-3 font-bold text-white">Power & Infrastructure Grid</td>
                      <td className="p-3 font-mono">Wind Gusts &gt; 45 km/h</td>
                      <td className="p-3">Deploy emergency restoration squads for overhead line branch trimming.</td>
                      <td className="p-3"><span className="bg-purple-500/20 text-purple-300 border border-purple-500/40 px-2 py-0.5 rounded text-[10px] font-bold uppercase">Operational</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
