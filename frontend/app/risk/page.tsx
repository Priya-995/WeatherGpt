"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { RiskResult, getRisk } from "@/lib/api";

const RiskMapClient = dynamic(() => import("@/components/RiskMapClient"), {
  ssr: false,
  loading: () => (
    <div className="h-[480px] bg-slate-900/60 rounded-xl border border-slate-800 flex items-center justify-center text-slate-400 text-sm">
      <span>Loading Interactive Leaflet Map...</span>
    </div>
  ),
});

export default function RiskMapPage() {
  const [selectedCoords, setSelectedCoords] = useState<{ lat: number; lon: number }>({
    lat: 28.6139,
    lon: 77.209,
  });
  const [riskData, setRiskData] = useState<RiskResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRisk() {
      setLoading(true);
      setError(null);
      try {
        const data = await getRisk(selectedCoords.lat, selectedCoords.lon);
        setRiskData(data);
      } catch (err: any) {
        setError(err.message || "Failed to calculate risk score.");
      } finally {
        setLoading(false);
      }
    }
    loadRisk();
  }, [selectedCoords]);

  const handleLocationClick = (lat: number, lon: number) => {
    setSelectedCoords({ lat, lon });
  };

  const getLevelBadgeClass = (level: string) => {
    switch (level.toLowerCase()) {
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

  const presetLocations = [
    { name: "Delhi / NCR", lat: 28.61, lon: 77.21 },
    { name: "Mumbai", lat: 19.07, lon: 72.87 },
    { name: "Uttar Pradesh (Agra)", lat: 27.18, lon: 78.01 },
    { name: "Rajasthan (Barmer)", lat: 27.2, lon: 70.9 },
    { name: "Goa", lat: 15.29, lon: 74.12 },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-slate-900/60 p-6 rounded-xl border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <span>🗺️</span> Early-Warning Risk Map
          </h1>
          <p className="text-sm text-slate-400">
            Click anywhere on the map to evaluate real-time weather hazard severity & sub-score breakdown.
          </p>
        </div>

        {/* Quick Presets */}
        <div className="flex flex-wrap gap-2">
          {presetLocations.map((p) => (
            <button
              key={p.name}
              onClick={() => setSelectedCoords({ lat: p.lat, lon: p.lon })}
              className="text-xs bg-slate-950 hover:bg-blue-600/30 text-slate-300 hover:text-white px-3 py-1.5 rounded-lg border border-slate-800 transition-colors font-medium"
            >
              {p.name}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map Container */}
        <div className="lg:col-span-2">
          <RiskMapClient
            onLocationSelect={handleLocationClick}
            selectedLocation={selectedCoords}
            riskLevel={riskData?.level || "low"}
          />
          <p className="text-xs text-slate-500 mt-2 text-center">
            💡 Click any point on the map to query the deterministic risk engine for those coordinates.
          </p>
        </div>

        {/* Risk Assessment Results Panel */}
        <div className="bg-slate-900/60 p-6 rounded-xl border border-slate-800 space-y-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Risk Assessment
              </span>
              <span className="text-xs font-mono text-slate-400">
                ({selectedCoords.lat.toFixed(2)}, {selectedCoords.lon.toFixed(2)})
              </span>
            </div>

            {loading ? (
              <div className="py-12 flex items-center justify-center text-slate-400 text-xs">
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mr-2" />
                Calculating risk level...
              </div>
            ) : error ? (
              <div className="py-4 text-xs text-red-400 bg-red-950/30 p-3 rounded border border-red-900">
                {error}
              </div>
            ) : riskData ? (
              <div className="space-y-4 mt-4">
                {/* Score & Level Badge */}
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-400">Composite Score</div>
                    <div className="text-3xl font-extrabold text-white">
                      {(riskData.score * 100).toFixed(0)} <span className="text-xs font-normal text-slate-400">/ 100</span>
                    </div>
                  </div>

                  <span
                    className={`text-sm uppercase font-extrabold px-3 py-1 rounded-md border ${getLevelBadgeClass(
                      riskData.level
                    )}`}
                  >
                    {riskData.level}
                  </span>
                </div>

                {/* Sub-Scores Breakdown */}
                <div className="space-y-2 bg-slate-950 p-3 rounded-lg border border-slate-800/80 text-xs">
                  <div className="font-semibold text-slate-300 mb-1">Sub-Score Breakdown:</div>
                  {Object.entries(riskData.sub_scores || {}).map(([key, val]) => (
                    <div key={key} className="flex justify-between items-center text-slate-400">
                      <span className="capitalize">{key.replace("_", " ")}</span>
                      <span className="font-mono font-medium text-slate-200">
                        {typeof val === "number" ? val.toFixed(2) : val}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Reasoning Factors */}
                <div className="space-y-1 text-xs">
                  <div className="font-semibold text-slate-300">Driver Factors:</div>
                  <ul className="list-disc list-inside space-y-1 text-slate-400">
                    {riskData.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}
          </div>

          {/* Summary Footer */}
          {riskData?.advisory?.summary && (
            <div className="pt-4 border-t border-slate-800 text-xs text-blue-300 bg-blue-950/20 p-3 rounded-lg border border-blue-900/30">
              <span className="font-bold text-blue-400">Advisory: </span>
              {riskData.advisory.summary}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
