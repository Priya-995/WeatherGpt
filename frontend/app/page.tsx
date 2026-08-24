"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Alert,
  LocationItem,
  WeatherResponse,
  getAlerts,
  getWeather,
  searchLocation,
} from "@/lib/api";

export default function DashboardPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<LocationItem[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<LocationItem>({
    name: "New Delhi",
    latitude: 28.6139,
    longitude: 77.209,
    country: "India",
  });
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch weather and alerts whenever selected location changes
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
        setError("Unable to load live weather data at the moment. Please check your connection and try again.");
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, [selectedLocation]);

  // Handle live search input
  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    try {
      const results = await searchLocation(query, 5);
      setSearchResults(results);
    } catch {
      setSearchResults([]);
    }
  };

  const selectLocation = (loc: LocationItem) => {
    setSelectedLocation(loc);
    setSearchQuery("");
    setSearchResults([]);
  };

  return (
    <div className="space-y-6">
      {/* Header & Location Search */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-slate-900/60 p-6 rounded-xl border border-slate-800 backdrop-blur-sm">
        <div>
          <h1 className="text-2xl font-bold text-white">Weather Dashboard</h1>
          <p className="text-sm text-slate-400">
            Real-time conditions and 7-day forecast for{" "}
            <span className="font-semibold text-blue-400">
              {selectedLocation.name}
              {selectedLocation.country ? `, ${selectedLocation.country}` : ""}
            </span>
          </p>
        </div>

        {/* Search Bar */}
        <div className="relative w-full md:w-80">
          <input
            type="text"
            placeholder="Search location (e.g. Noida, Paris)..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 text-white rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500 transition-colors"
          />

          {searchResults.length > 0 && (
            <ul className="absolute left-0 right-0 top-full mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-xl z-50 max-h-60 overflow-y-auto divide-y divide-slate-800">
              {searchResults.map((item, idx) => (
                <li
                  key={idx}
                  onClick={() => selectLocation(item)}
                  className="p-3 text-sm hover:bg-blue-600/20 cursor-pointer text-slate-200 hover:text-white transition-colors"
                >
                  <div className="font-medium">{item.name}</div>
                  <div className="text-xs text-slate-400">
                    {item.admin1 ? `${item.admin1}, ` : ""}
                    {item.country || ""}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Active Alerts Banner */}
      {alerts.length > 0 && (
        <div className="bg-gradient-to-r from-amber-900/40 via-red-900/40 to-amber-900/40 border border-amber-500/40 p-4 rounded-xl flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-3 h-3 rounded-full bg-red-500 animate-ping" />
            <div>
              <h3 className="font-semibold text-amber-200 text-sm">
                Active Weather Warnings ({alerts.length})
              </h3>
              <p className="text-xs text-amber-300/80">
                {alerts[0].affected_location}: {alerts[0].instructions?.slice(0, 120)}...
              </p>
            </div>
          </div>
          <Link
            href="/alerts"
            className="text-xs font-semibold bg-amber-500 text-slate-950 px-3 py-1.5 rounded-md hover:bg-amber-400 transition-colors shrink-0"
          >
            View Alert Center
          </Link>
        </div>
      )}

      {loading ? (
        <div className="h-64 flex items-center justify-center bg-slate-900/40 rounded-xl border border-slate-800">
          <div className="text-slate-400 text-sm flex items-center space-x-2">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span>Loading live weather conditions...</span>
          </div>
        </div>
      ) : error ? (
        <div className="p-4 bg-red-900/30 border border-red-800 rounded-xl text-red-300 text-sm">
          {error}
        </div>
      ) : weather ? (
        <>
          {/* Current Weather Card */}
          <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-blue-950/40 p-6 rounded-xl border border-slate-800 shadow-lg grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex flex-col justify-between">
              <div>
                <span className="text-xs font-medium uppercase tracking-wider text-blue-400">
                  Current Conditions
                </span>
                <div className="text-5xl font-extrabold text-white mt-2">
                  {weather.current.temperature_2m.toFixed(1)}°C
                </div>
                <div className="text-xs text-slate-400 mt-1">
                  Feels like {weather.current.apparent_temperature.toFixed(1)}°C
                </div>
              </div>
              <div className="text-xs text-slate-400 mt-4">
                {weather.cached ? "⚡ Fast cached response" : "🔄 Live telemetry"}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm bg-slate-950/50 p-4 rounded-lg border border-slate-800/80 md:col-span-2">
              <div>
                <span className="text-xs text-slate-400">Humidity</span>
                <div className="font-semibold text-slate-100 text-lg">
                  {weather.current.relative_humidity_2m}%
                </div>
              </div>
              <div>
                <span className="text-xs text-slate-400">Precipitation</span>
                <div className="font-semibold text-slate-100 text-lg">
                  {weather.current.precipitation} mm
                </div>
              </div>
              <div>
                <span className="text-xs text-slate-400">Wind Speed</span>
                <div className="font-semibold text-slate-100 text-lg">
                  {weather.current.wind_speed_10m} km/h
                </div>
              </div>
              <div>
                <span className="text-xs text-slate-400">Cloud Cover</span>
                <div className="font-semibold text-slate-100 text-lg">
                  {weather.current.cloud_cover}%
                </div>
              </div>
            </div>
          </div>

          {/* 7-Day Forecast Summary */}
          <div className="bg-slate-900/60 p-6 rounded-xl border border-slate-800">
            <h2 className="text-lg font-bold text-white mb-4">7-Day Forecast</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
              {weather.daily.time.map((day, idx) => (
                <div
                  key={day}
                  className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 text-center flex flex-col justify-between"
                >
                  <div className="text-xs font-semibold text-slate-400">
                    {new Date(day).toLocaleDateString("en-US", { weekday: "short", month: "numeric", day: "numeric" })}
                  </div>
                  <div className="my-2">
                    <div className="text-base font-bold text-white">
                      {weather.daily.temperature_2m_max[idx].toFixed(0)}°
                    </div>
                    <div className="text-xs text-slate-400">
                      {weather.daily.temperature_2m_min[idx].toFixed(0)}°
                    </div>
                  </div>
                  <div className="text-[10px] text-blue-300 bg-blue-950/40 py-0.5 rounded border border-blue-900/40">
                    🌧️ {weather.daily.precipitation_probability_max[idx]}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : null}

      {/* Ask WeatherGPT CTA Banner */}
      <div className="bg-gradient-to-r from-blue-900/50 to-indigo-900/50 p-6 rounded-xl border border-blue-800/50 flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Have detailed weather questions?</h2>
          <p className="text-sm text-slate-300 mt-1">
            Ask WeatherGPT in natural language for grounded forecasts, travel safety, and agricultural insights.
          </p>
        </div>
        <Link
          href="/chat"
          className="bg-blue-600 hover:bg-blue-500 text-white font-semibold px-6 py-2.5 rounded-lg text-sm transition-colors shrink-0 shadow-lg shadow-blue-600/30"
        >
          Ask WeatherGPT AI →
        </Link>
      </div>
    </div>
  );
}
