"use client";

import { useEffect, useState } from "react";
import { RiskResult, getRisk } from "@/lib/api";
import AdvisoryTabCard from "@/components/ui/AdvisoryTabCard";
import { useLocation } from "@/context/LocationContext";
import { ClipboardList, MapPin } from "lucide-react";

// Persona Advisory Panel Page - WeatherGPT Early Warning System
export default function AdvisoryPage() {
  const { selectedLocation } = useLocation();
  const [activeTab, setActiveTab] = useState<"citizen" | "farmer" | "official">("citizen");
  const [riskData, setRiskData] = useState<RiskResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const rData = await getRisk(selectedLocation.lat, selectedLocation.lon, activeTab);
        setRiskData(rData);
      } catch (err) {
        console.error("Error loading advisory telemetry:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [selectedLocation, activeTab]);

  return (
    <div className="space-y-6 max-w-[1440px] mx-auto">
      {/* Top Header */}
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
            Tailored safety directives, hazard trends, and emergency protocols for citizens, farmers, and emergency officials.
          </p>
        </div>

        {/* Selected State Badge */}
        <div className="shrink-0 flex items-center gap-2 bg-surface-container-low px-4 py-2.5 rounded-xl border border-outline-variant/40 text-xs font-bold text-on-surface">
          <MapPin className="w-4 h-4 text-primary" />
          <span>Active State: <strong className="text-primary">{selectedLocation.displayName}</strong></span>
        </div>
      </div>

      {/* Main Advisory Tab Component */}
      {loading ? (
        <div className="h-64 flex flex-col items-center justify-center bg-surface-container-low rounded-xl border border-surface-container-high space-y-3">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-body-sm text-on-surface-variant font-semibold">
            Evaluating persona advisory telemetry for {selectedLocation.displayName}...
          </span>
        </div>
      ) : (
        <AdvisoryTabCard
          riskData={riskData}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
      )}
    </div>
  );
}
