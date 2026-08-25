"use client";

import React from "react";
import { WeatherResponse } from "@/lib/api";
import {
  Thermometer,
  Wind,
  Droplets,
  CloudRain,
  Cloud,
  Zap,
  RefreshCw,
} from "lucide-react";

interface WeatherCardProps {
  weather: WeatherResponse;
  locationName?: string;
  className?: string;
}

export default function WeatherCard({ weather, locationName, className = "" }: WeatherCardProps) {
  const current = weather.current;

  const getWeatherDescription = (code: number) => {
    if (code === 0) return "Clear Sky";
    if (code === 1 || code === 2 || code === 3) return "Partly Cloudy";
    if (code >= 45 && code <= 48) return "Foggy / Mist";
    if (code >= 51 && code <= 67) return "Rain / Drizzle";
    if (code >= 71 && code <= 77) return "Snowfall";
    if (code >= 80 && code <= 82) return "Rain Showers";
    if (code >= 95) return "Thunderstorm Alert";
    return "Variable Weather";
  };

  return (
    <div
      className={`bg-slate-900 p-6 rounded-2xl border border-slate-800 shadow-xl grid grid-cols-1 md:grid-cols-3 gap-6 ${className}`}
    >
      {/* Main Temperature & Primary State */}
      <div className="flex flex-col justify-between space-y-4">
        <div>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Thermometer className="w-4 h-4 text-slate-400" />
              Current Conditions
            </span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-slate-950 border border-slate-800 text-slate-400 flex items-center gap-1">
              {weather.cached ? (
                <>
                  <Zap className="w-3 h-3 text-slate-400" />
                  Cached
                </>
              ) : (
                <>
                  <RefreshCw className="w-3 h-3 text-slate-400 animate-spin" style={{ animationDuration: "6s" }} />
                  Live Telemetry
                </>
              )}
            </span>
          </div>

          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-5xl font-extrabold text-white tracking-tight">
              {current.temperature_2m.toFixed(1)}°C
            </span>
            <span className="text-sm font-semibold text-slate-400">
              Feels like {current.apparent_temperature.toFixed(1)}°C
            </span>
          </div>

          <p className="text-sm font-medium text-slate-300 mt-2 flex items-center gap-1.5">
            <Cloud className="w-4 h-4 text-slate-400" />
            {getWeatherDescription(current.weather_code)}
          </p>
        </div>

        <div className="text-xs text-slate-500 font-mono pt-2 border-t border-slate-800/80">
          Lat {weather.latitude.toFixed(2)}° N, Lon {weather.longitude.toFixed(2)}° E • Elev {weather.elevation}m
        </div>
      </div>

      {/* Stat Chips Grid - ALL USE UNIFORM MUTED SLATE ICONS (NO RAINBOW COLORS) */}
      <div className="grid grid-cols-2 gap-3 bg-slate-950 p-4 rounded-xl border border-slate-800/80 md:col-span-2">
        <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 flex items-center space-x-3">
          <div className="p-2 bg-slate-800/60 text-slate-400 rounded-lg shrink-0 border border-slate-700/40">
            <Droplets className="w-5 h-5 text-slate-400" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Relative Humidity</div>
            <div className="text-base font-bold text-white mt-0.5">
              {current.relative_humidity_2m}%
            </div>
          </div>
        </div>

        <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 flex items-center space-x-3">
          <div className="p-2 bg-slate-800/60 text-slate-400 rounded-lg shrink-0 border border-slate-700/40">
            <CloudRain className="w-5 h-5 text-slate-400" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Precipitation</div>
            <div className="text-base font-bold text-white mt-0.5">
              {current.precipitation} mm
            </div>
          </div>
        </div>

        <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 flex items-center space-x-3">
          <div className="p-2 bg-slate-800/60 text-slate-400 rounded-lg shrink-0 border border-slate-700/40">
            <Wind className="w-5 h-5 text-slate-400" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Wind Velocity</div>
            <div className="text-base font-bold text-white mt-0.5">
              {current.wind_speed_10m} km/h
            </div>
          </div>
        </div>

        <div className="bg-slate-900 p-3 rounded-lg border border-slate-800 flex items-center space-x-3">
          <div className="p-2 bg-slate-800/60 text-slate-400 rounded-lg shrink-0 border border-slate-700/40">
            <Cloud className="w-5 h-5 text-slate-400" />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Cloud Cover</div>
            <div className="text-base font-bold text-white mt-0.5">
              {current.cloud_cover}%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
