"use client";

import { useEffect, useState } from "react";
import { RiskResult, getWeather, getRisk } from "@/lib/api";
import AdvisoryTabCard from "@/components/ui/AdvisoryTabCard";
import { ClipboardList, MapPin } from "lucide-react";

export default function AdvisoryPage() {
  const [selectedCoords, setSelectedCoords] = useState<{ name: string; lat: number; lon: number }>({
    name: "Delhi / NCR",
    lat: 28.61,
    lon: 77.21,
  });
  const [riskData, setRiskData] = useState<RiskResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const rData = await getRisk(selectedCoords.lat, selectedCoords.lon);
        setRiskData(rData);
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

  return (
    <div className="space-y-6 max-w-[1440px] mx-auto">
      {/* Top Header & Preset Pills */}
      <div className="bg-surface-container-lowest p-6 sm:p-8 rounded-xl border border-surface-container-high shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center space-x-2 text-label-caps text-on-surface-variant">
            <ClipboardList className="w-4 h-4 text-primary" />
            <span>Decision Support & Action Directives</span>
          </div>
          <h1 className="text-headline-lg font-bold text-on-surface tracking-tight">
            Persona Advisory Panel
          </h1>
          <p className="text-body-sm text-on-surface-variant max-w-2xl">
            Tailored safety directives, hazard trends, and emergency protocols for citizens, farmers, and heat safety managers.
          </p>
        </div>

        <div className="flex flex-wrap gap-2 shrink-0">
          {presetLocations.map((loc) => (
            <button
              key={loc.name}
              type="button"
              onClick={() => setSelectedCoords(loc)}
              className={`text-xs px-3.5 py-2 rounded-lg border transition-all font-semibold flex items-center gap-1 ${
                selectedCoords.name === loc.name
                  ? "bg-primary text-on-primary border-primary shadow-sm"
                  : "bg-surface-container-low text-on-surface-variant border-outline-variant/40 hover:text-on-surface"
              }`}
            >
              <MapPin className="w-3.5 h-3.5" />
              <span>{loc.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Stitch Advisory Tab Component */}
      {loading ? (
        <div className="h-64 flex flex-col items-center justify-center bg-surface-container-low rounded-xl border border-surface-container-high space-y-3">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-body-sm text-on-surface-variant font-semibold">
            Evaluating persona advisory telemetry for {selectedCoords.name}...
          </span>
        </div>
      ) : (
        <AdvisoryTabCard riskData={riskData} />
      )}
    </div>
  );
}
