"use client";

import React from "react";
import { DailyForecast } from "@/lib/api";
import { Calendar, Sun, CloudRain, CloudLightning, CloudSun } from "lucide-react";

interface ForecastStripProps {
  daily: DailyForecast;
  className?: string;
}

export default function ForecastStrip({ daily, className = "" }: ForecastStripProps) {
  if (!daily || !daily.time || daily.time.length === 0) return null;

  const days = daily.time.slice(0, 7);

  const getWeatherIcon = (code: number, rainProb: number) => {
    if (code >= 95) return <CloudLightning className="w-5 h-5 text-slate-400" />;
    if (code >= 51 || rainProb > 50) return <CloudRain className="w-5 h-5 text-slate-400" />;
    if (code >= 1 && code <= 3) return <CloudSun className="w-5 h-5 text-slate-400" />;
    return <Sun className="w-5 h-5 text-slate-400" />;
  };

  return (
    <div className={`bg-slate-900 p-6 rounded-2xl border border-slate-800 space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Calendar className="w-4 h-4 text-slate-400" />
          <span>7-Day Meteorological Forecast</span>
        </h2>
        <span className="text-xs text-slate-400 font-mono">NWP-GFS Guidance</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {days.map((dayStr, idx) => {
          const dateObj = new Date(dayStr);
          const dayName = idx === 0 ? "Today" : dateObj.toLocaleDateString("en-US", { weekday: "short" });
          const dateSub = dateObj.toLocaleDateString("en-US", { month: "short", day: "numeric" });
          const maxTemp = daily.temperature_2m_max[idx]?.toFixed(0) ?? "--";
          const minTemp = daily.temperature_2m_min[idx]?.toFixed(0) ?? "--";
          const rainProb = daily.precipitation_probability_max[idx] ?? 0;
          const weatherCode = daily.weather_code[idx] ?? 0;

          return (
            <div
              key={dayStr}
              className="bg-slate-950 p-3.5 rounded-xl border border-slate-800/80 text-center flex flex-col justify-between hover:border-slate-700 transition-all group"
            >
              <div>
                <div className="text-xs font-bold text-slate-200 group-hover:text-white">{dayName}</div>
                <div className="text-[10px] text-slate-400 font-medium">{dateSub}</div>
              </div>

              <div className="my-3 flex flex-col items-center gap-1">
                {getWeatherIcon(weatherCode, rainProb)}
                <div className="mt-1 flex items-baseline justify-center gap-1">
                  <span className="text-lg font-black text-white">{maxTemp}°</span>
                  <span className="text-xs font-semibold text-slate-400">{minTemp}°</span>
                </div>
              </div>

              <div className="text-[10px] font-medium text-slate-300 bg-slate-900 py-1 px-1.5 rounded border border-slate-800 flex items-center justify-center gap-1">
                <span>Rain {rainProb}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
