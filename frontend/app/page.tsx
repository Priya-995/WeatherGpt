"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Alert,
  LocationItem,
  WeatherResponse,
  getAlerts,
  getWeather,
} from "@/lib/api";
import LocationSearch from "@/components/ui/LocationSearch";
import AlertBanner from "@/components/ui/AlertBanner";
import WeatherMetricCard from "@/components/ui/WeatherMetricCard";
import ForecastStrip from "@/components/ui/ForecastStrip";
import RiskFactorCard from "@/components/ui/RiskFactorCard";
import { MapPin, ArrowRight, Bot, ShieldCheck } from "lucide-react";

export default function DashboardPage() {
  const [selectedLocation, setSelectedLocation] = useState<LocationItem>({
    name: "New Delhi",
    latitude: 28.6139,
    longitude: 77.209,
    country: "India",
    admin1: "Delhi",
  });
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboardData() {
      setLoading(true);
      setError(null);
      try {
        const [weatherData, alertData] = await Promise.all([
          getWeather(selectedLocation.latitude, selectedLocation.longitude),
          getAlerts(selectedLocation.latitude, selectedLocation.longitude),
        ]);
        setWeather(weatherData);
        setAlerts(alertData.alerts || []);
      } catch {
        setError("Unable to load live weather telemetry.");
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, [selectedLocation]);

  const selectLocation = (loc: LocationItem) => {
    setSelectedLocation(loc);
  };

  // Derive risk factors dynamically from telemetry
  const temp = weather?.current?.temperature_2m ?? 28;
  const rain = weather?.current?.precipitation ?? 0;
  const wind = weather?.current?.wind_speed_10m ?? 12;

  const floodScore = Math.min(100, Math.round(rain * 2.5 + 10));
  const stormScore = Math.min(100, Math.round(wind * 1.8 + rain * 0.5));
  const heatScore = Math.min(100, Math.round((temp / 45) * 100));
  const windScore = Math.min(100, Math.round((wind / 60) * 100));

  return (
    <div className="space-y-6 max-w-[1440px] mx-auto">
      {/* Location Header & Search Bar */}
      <div className="bg-surface-container-lowest p-6 rounded-xl border border-surface-container-high shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1">
          <div className="flex items-center space-x-2 text-label-caps text-on-surface-variant">
            <MapPin className="w-4 h-4 text-primary" />
            <span>Target Location Telemetry</span>
          </div>
          <h1 className="text-headline-lg font-bold text-on-surface tracking-tight flex items-center gap-2">
            <span>{selectedLocation.name}</span>
            {selectedLocation.country && (
              <span className="text-body-md font-normal text-on-surface-variant">
                ({selectedLocation.admin1 ? `${selectedLocation.admin1}, ` : ""}
                {selectedLocation.country})
              </span>
            )}
          </h1>
          <p className="text-body-sm text-on-surface-variant">
            Real-time atmospheric telemetry, NWP forecast grids, and official IMD warnings.
          </p>
        </div>

        <div className="w-full md:w-80 shrink-0">
          <LocationSearch
            onSelectLocation={selectLocation}
            selectedLocation={selectedLocation}
          />
        </div>
      </div>

      {/* Active Alerts Banner (rendered only when an alert exists) */}
      <AlertBanner alerts={alerts} />

      {/* Loading Skeleton / Weather Content */}
      {loading ? (
        <div className="space-y-6">
          <div className="h-64 bg-surface-container-low rounded-xl border border-surface-container-high flex items-center justify-center space-x-3 text-on-surface-variant text-body-sm">
            <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span>Connecting to NWP telemetry & forecast engines...</span>
          </div>
        </div>
      ) : error ? (
        <div className="p-6 bg-error-container/60 border border-error/40 rounded-xl text-on-error-container text-body-sm">
          {error}
        </div>
      ) : weather ? (
        <>
          {/* Current Conditions Hero Metric Card */}
          <WeatherMetricCard weather={weather} locationName={selectedLocation.name} />

          {/* 7-Day Forecast Strip */}
          <ForecastStrip daily={weather.daily} />

          {/* 4-Tile Location Risk Assessment Grid */}
          <div className="space-y-3">
            <h2 className="text-headline-sm font-bold text-on-surface flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-primary" />
              <span>Location Risk Assessment Grid</span>
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <RiskFactorCard
                label="Flood Risk"
                value={`${floodScore}/100`}
                percentage={floodScore}
                severity={floodScore >= 70 ? "critical" : floodScore >= 40 ? "moderate" : "low"}
                subtext="Evaluated against precipitation runoff metrics."
              />
              <RiskFactorCard
                label="Storm Severity"
                value={`${stormScore}/100`}
                percentage={stormScore}
                severity={stormScore >= 70 ? "high" : stormScore >= 40 ? "moderate" : "low"}
                subtext="Based on wind gusts and convective potential."
              />
              <RiskFactorCard
                label="Heat Index"
                value={`${heatScore}/100`}
                percentage={heatScore}
                severity={heatScore >= 75 ? "critical" : heatScore >= 50 ? "high" : "low"}
                subtext="Apparent thermal desiccation index."
              />
              <RiskFactorCard
                label="Wind Damage"
                value={`${windScore}/100`}
                percentage={windScore}
                severity={windScore >= 60 ? "moderate" : "low"}
                subtext="Structural wind strain calculation."
              />
            </div>
          </div>
        </>
      ) : null}

      {/* Ask WeatherGPT CTA Card */}
      <div className="bg-primary-container p-6 sm:p-8 rounded-xl border border-primary/20 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-2xl text-on-primary-container">
          <div className="flex items-center space-x-2 text-label-caps font-bold">
            <Bot className="w-4 h-4 text-on-primary-container" />
            <span>Natural Language Weather Intelligence</span>
          </div>
          <h2 className="text-headline-md font-bold tracking-tight">
            Have specific questions about local weather or agricultural timing?
          </h2>
          <p className="text-body-sm opacity-90 leading-relaxed">
            Ask WeatherGPT in natural language (English, Hinglish, or Hindi) for grounded forecasts, travel safety guidelines, and crop spraying advice.
          </p>
        </div>

        <Link
          href="/chat"
          className="bg-primary hover:bg-primary-container text-on-primary font-bold px-6 py-3 rounded-lg text-body-sm transition-all shadow-md flex items-center space-x-2 shrink-0 group"
        >
          <span>Ask WeatherGPT AI</span>
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </Link>
      </div>
    </div>
  );
}
