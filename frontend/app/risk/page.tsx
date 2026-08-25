"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { RiskResult, getRisk } from "@/lib/api";
import SeverityBadge from "@/components/ui/SeverityBadge";
import {
  Compass,
  Activity,
  AlertTriangle,
  FileCheck,
  Map as MapIcon,
  MousePointerClick,
  Info,
} from "lucide-react";

const RiskMapClient = dynamic(() => import("@/components/RiskMapClient"), {
  ssr: false,
  loading: () => (
    <div className="h-[520px] bg-surface-container-low rounded-xl border border-surface-container-high flex items-center justify-center text-on-surface-variant text-body-sm space-x-2">
      <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      <span>Initializing Interactive GIS Map Engine...</span>
    </div>
  ),
});

const formatValue = (val: any): string => {
  if (val === undefined || val === null) return "";
  if (typeof val === "object") return "";
  return String(val);
};

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
      } catch {
        setError("Unable to compute risk score matrix for selected location.");
      } finally {
        setLoading(false);
      }
    }
    loadRisk();
  }, [selectedCoords]);

  const handleLocationClick = (lat: number, lon: number) => {
    setSelectedCoords({ lat, lon });
  };

  const presetLocations = [
    { name: "Delhi / NCR", lat: 28.61, lon: 77.21 },
    { name: "Mumbai", lat: 19.07, lon: 72.87 },
    { name: "Uttar Pradesh (Agra)", lat: 27.18, lon: 78.01 },
    { name: "Rajasthan (Barmer)", lat: 27.2, lon: 70.9 },
    { name: "Goa Coast", lat: 15.29, lon: 74.12 },
  ];

  return (
    <div className="space-y-6 max-w-[1440px] mx-auto">
      {/* Header Bar & Presets */}
      <div className="bg-surface-container-lowest p-6 rounded-xl border border-surface-container-high shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2 text-label-caps text-on-surface-variant">
            <MapIcon className="w-4 h-4 text-primary" />
            <span>Early-Warning GIS Risk Map</span>
          </div>
          <h1 className="text-headline-lg font-bold text-on-surface tracking-tight">
            Interactive Risk Assessment Grid
          </h1>
          <p className="text-body-sm text-on-surface-variant">
            Click any coordinate point to compute composite risk scores and factor weightings.
          </p>
        </div>

        <div className="flex flex-wrap gap-2 shrink-0">
          {presetLocations.map((p) => (
            <button
              key={p.name}
              type="button"
              onClick={() => setSelectedCoords({ lat: p.lat, lon: p.lon })}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-all font-semibold ${
                selectedCoords.lat === p.lat && selectedCoords.lon === p.lon
                  ? "bg-primary text-on-primary border-primary shadow-sm"
                  : "bg-surface-container-low text-on-surface-variant border-outline-variant/40 hover:text-on-surface"
              }`}
            >
              📍 {p.name}
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid: Full-bleed Map (Left) + Right Slide-in Detail Panel (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Full-bleed Map on Left (2 cols) */}
        <div className="lg:col-span-2 space-y-2">
          <RiskMapClient
            onLocationSelect={handleLocationClick}
            selectedLocation={selectedCoords}
            riskLevel={riskData?.level || "low"}
          />
          <div className="text-xs text-outline flex items-center justify-center space-x-1.5 pt-1">
            <MousePointerClick className="w-3.5 h-3.5 text-primary" />
            <span>Click any location on the map to evaluate coordinates & hazard factors.</span>
          </div>
        </div>

        {/* Right-Hand Detail Panel */}
        <div className="bg-surface-container-lowest p-6 rounded-xl border border-surface-container-high shadow-sm space-y-5 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-surface-container-high pb-3">
              <span className="text-label-caps text-on-surface-variant font-bold flex items-center gap-1.5">
                <Compass className="w-4 h-4 text-primary" />
                Selected Coordinates
              </span>
              <span className="text-xs font-mono font-bold text-primary bg-surface-container-low px-2.5 py-0.5 rounded border border-outline-variant/40">
                {selectedCoords.lat.toFixed(2)}°N, {selectedCoords.lon.toFixed(2)}°E
              </span>
            </div>

            {loading ? (
              <div className="py-16 flex flex-col items-center justify-center space-y-3 text-on-surface-variant text-body-sm">
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                <span>Calculating risk matrix...</span>
              </div>
            ) : error ? (
              <div className="py-4 text-body-sm text-on-error-container bg-error-container p-4 rounded-xl border border-error/30">
                {error}
              </div>
            ) : riskData ? (
              <div className="space-y-4">
                {/* Large Composite Risk Score + Severity Badge */}
                <div className="bg-surface-container-low p-4 rounded-xl border border-surface-container-high flex items-center justify-between">
                  <div>
                    <div className="text-label-caps text-on-surface-variant">Composite Risk Score</div>
                    <div className="text-metric-display text-primary mt-1">
                      {typeof riskData.score === "number" ? Math.round(riskData.score * 100) : "0"}{" "}
                      <span className="text-body-sm font-normal text-on-surface-variant">/ 100</span>
                    </div>
                  </div>

                  <SeverityBadge severity={riskData.level} size="lg" />
                </div>

                {/* Prototype Disclaimer */}
                <div className="text-[11px] text-outline italic flex items-center gap-1 font-mono">
                  <Info className="w-3.5 h-3.5 shrink-0" />
                  <span>* Prototype decision-support score based on NWP & IMD thresholds</span>
                </div>

                {/* Factor Breakdown List (Rainfall/Wind/IMD Alert Weighting) */}
                <div className="space-y-3 pt-2">
                  <div className="text-label-caps text-on-surface font-bold flex items-center gap-1">
                    <Activity className="w-3.5 h-3.5 text-primary" />
                    Factor Breakdown:
                  </div>

                  <div className="space-y-2 text-body-sm">
                    <div className="bg-surface-container-low p-3 rounded-lg border border-outline-variant/30 flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-on-surface">Rainfall Hazard</div>
                        <div className="text-xs text-on-surface-variant">35% Weighting</div>
                      </div>
                      <SeverityBadge severity={riskData.score >= 0.6 ? "high" : "low"} size="sm" />
                    </div>

                    <div className="bg-surface-container-low p-3 rounded-lg border border-outline-variant/30 flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-on-surface">Wind Velocity Hazard</div>
                        <div className="text-xs text-on-surface-variant">25% Weighting</div>
                      </div>
                      <SeverityBadge severity={riskData.score >= 0.7 ? "critical" : "moderate"} size="sm" />
                    </div>

                    <div className="bg-surface-container-low p-3 rounded-lg border border-outline-variant/30 flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-on-surface">IMD Alert Weighting</div>
                        <div className="text-xs text-on-surface-variant">15% Weighting</div>
                      </div>
                      <SeverityBadge severity="moderate" size="sm" />
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          {/* Bottom Summary */}
          {riskData?.advisory?.summary && (
            <div className="pt-3 border-t border-surface-container-high text-xs text-on-surface-variant space-y-1">
              <div className="font-bold text-on-surface flex items-center gap-1">
                <FileCheck className="w-3.5 h-3.5 text-primary" />
                Executive Summary:
              </div>
              <p className="leading-relaxed">
                {typeof riskData.advisory.summary === "object"
                  ? JSON.stringify(riskData.advisory.summary)
                  : String(riskData.advisory.summary)}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
