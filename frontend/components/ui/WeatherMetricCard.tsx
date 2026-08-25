"use client";

import React from "react";
import { WeatherResponse } from "@/lib/api";
import { Thermometer, Wind, Droplets, CloudRain, Cloud, Zap, RefreshCw } from "lucide-react";

interface WeatherMetricCardProps {
  weather: WeatherResponse;
  locationName?: string;
  className?: string;
}

export default function WeatherMetricCard({
  weather,
  locationName = "New Delhi",
  className = "",
}: WeatherMetricCardProps) {
  const current = weather.current;

  const getWeatherDescription = (code: number) => {
    if (code === 0) return "Clear Sky";
    if (code >= 1 && code <= 3) return "Partly Cloudy";
    if (code >= 45 && code <= 48) return "Foggy / Mist";
    if (code >= 51 && code <= 67) return "Light Rain / Drizzle";
    if (code >= 80 && code <= 82) return "Rain Showers";
    if (code >= 95) return "Thunderstorm Warning";
    return "Variable Conditions";
  };

  return (
    <div
      className={`bg-surface-container-lowest p-6 rounded-xl border border-surface-container-high shadow-sm grid grid-cols-1 md:grid-cols-3 gap-6 ${className}`}
    >
      {/* Primary Hero Temperature Section */}
      <div className="flex flex-col justify-between space-y-4">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-label-caps text-on-surface-variant flex items-center gap-1.5">
              <Thermometer className="w-4 h-4 text-outline" />
              Current Telemetry
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container text-on-surface-variant flex items-center gap-1">
              {weather.cached ? (
                <>
                  <Zap className="w-3 h-3 text-outline" />
                  Cached
                </>
              ) : (
                <>
                  <RefreshCw className="w-3 h-3 text-primary animate-spin" style={{ animationDuration: "6s" }} />
                  Live NWP
                </>
              )}
            </span>
          </div>

          <div className="mt-4 flex items-baseline gap-3">
            <span className="text-metric-display text-primary tracking-tight">
              {current.temperature_2m.toFixed(1)}°C
            </span>
            <span className="text-body-sm text-on-surface-variant font-medium">
              Feels like {current.apparent_temperature.toFixed(1)}°C
            </span>
          </div>

          <p className="text-body-md font-semibold text-on-surface mt-2 flex items-center gap-2">
            <Cloud className="w-4 h-4 text-outline" />
            {getWeatherDescription(current.weather_code)}
          </p>
        </div>

        <div className="text-xs text-outline font-mono pt-2 border-t border-surface-container-high">
          Lat {weather.latitude.toFixed(2)}°N, Lon {weather.longitude.toFixed(2)}°E • Elev {weather.elevation}m
        </div>
      </div>

      {/* 4 Stat Chips Grid */}
      <div className="grid grid-cols-2 gap-3 bg-surface-container-low p-4 rounded-xl border border-surface-container-high md:col-span-2">
        <div className="bg-surface-container-lowest p-3.5 rounded-lg border border-surface-container-high flex items-center space-x-3">
          <div className="p-2.5 bg-surface-container text-on-surface-variant rounded-lg shrink-0">
            <Droplets className="w-5 h-5 text-outline" />
          </div>
          <div>
            <div className="text-label-caps text-on-surface-variant">Humidity</div>
            <div className="text-headline-sm font-bold text-on-surface mt-0.5">
              {current.relative_humidity_2m}%
            </div>
          </div>
        </div>

        <div className="bg-surface-container-lowest p-3.5 rounded-lg border border-surface-container-high flex items-center space-x-3">
          <div className="p-2.5 bg-surface-container text-on-surface-variant rounded-lg shrink-0">
            <CloudRain className="w-5 h-5 text-outline" />
          </div>
          <div>
            <div className="text-label-caps text-on-surface-variant">Precipitation</div>
            <div className="text-headline-sm font-bold text-on-surface mt-0.5">
              {current.precipitation} mm
            </div>
          </div>
        </div>

        <div className="bg-surface-container-lowest p-3.5 rounded-lg border border-surface-container-high flex items-center space-x-3">
          <div className="p-2.5 bg-surface-container text-on-surface-variant rounded-lg shrink-0">
            <Wind className="w-5 h-5 text-outline" />
          </div>
          <div>
            <div className="text-label-caps text-on-surface-variant">Wind Speed</div>
            <div className="text-headline-sm font-bold text-on-surface mt-0.5">
              {current.wind_speed_10m} km/h
            </div>
          </div>
        </div>

        <div className="bg-surface-container-lowest p-3.5 rounded-lg border border-surface-container-high flex items-center space-x-3">
          <div className="p-2.5 bg-surface-container text-on-surface-variant rounded-lg shrink-0">
            <Cloud className="w-5 h-5 text-outline" />
          </div>
          <div>
            <div className="text-label-caps text-on-surface-variant">Cloud Cover</div>
            <div className="text-headline-sm font-bold text-on-surface mt-0.5">
              {current.cloud_cover}%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
