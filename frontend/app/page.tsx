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
import {
  MapPin,
  ArrowRight,
  Bot,
  ShieldCheck,
  Sun,
  Moon,
  Cloud,
  CloudRain,
  CloudLightning,
  Snowflake,
  CloudFog,
} from "lucide-react";

type WeatherTheme =
  | "clear"
  | "cloudy"
  | "rainy"
  | "stormy"
  | "snowy"
  | "foggy"
  | "night";

type TimePeriod =
  | "morning"
  | "afternoon"
  | "evening"
  | "night";

type VideoBackground = {
  period: TimePeriod;
  video: string;
};

function getTimeBasedVideo(date: Date): VideoBackground {
  const hour = date.getHours();

  // 5:00 AM to 9:00 AM
  if (hour >= 5 && hour < 9) {
    return {
      period: "morning",
      video: "/videos/sunset.mp4",
    };
  }

  // 9:00 AM to 3:00 PM
  if (hour >= 9 && hour < 15) {
    return {
      period: "afternoon",
      video: "/videos/AfterNoon.mp4",
    };
  }

  // 3:00 PM to 6:00 PM
  if (hour >= 15 && hour < 18) {
    return {
      period: "evening",
      video: "/videos/sunset.mp4",
    };
  }

  // 6:00 PM to 5:00 AM
  return {
    period: "night",
    video: "/videos/Night.mp4",
  };
}

function getWeatherTheme(
  weatherCode?: number,
  isDay: number = 1
): WeatherTheme {
  if (weatherCode === undefined) {
    return isDay === 0 ? "night" : "clear";
  }

  // Thunderstorm
  if ([95, 96, 99].includes(weatherCode)) {
    return "stormy";
  }

  // Rain and drizzle
  if (
    [
      51, 53, 55, 56, 57,
      61, 63, 65, 66, 67,
      80, 81, 82,
    ].includes(weatherCode)
  ) {
    return "rainy";
  }

  // Snow
  if ([71, 73, 75, 77, 85, 86].includes(weatherCode)) {
    return "snowy";
  }

  // Fog
  if ([45, 48].includes(weatherCode)) {
    return "foggy";
  }

  // Clear/cloudy night
  if (isDay === 0) {
    return "night";
  }

  // Partly cloudy and overcast
  if ([1, 2, 3].includes(weatherCode)) {
    return "cloudy";
  }

  return "clear";
}

const themeLabels: Record<WeatherTheme, string> = {
  clear: "Clear weather",
  cloudy: "Cloudy weather",
  rainy: "Rainy weather",
  stormy: "Thunderstorm conditions",
  snowy: "Snowy weather",
  foggy: "Foggy conditions",
  night: "Night conditions",
};

function WeatherThemeIcon({
  theme,
  className = "w-5 h-5",
}: {
  theme: WeatherTheme;
  className?: string;
}) {
  if (theme === "clear") {
    return <Sun className={className} />;
  }

  if (theme === "cloudy") {
    return <Cloud className={className} />;
  }

  if (theme === "rainy") {
    return <CloudRain className={className} />;
  }

  if (theme === "stormy") {
    return <CloudLightning className={className} />;
  }

  if (theme === "snowy") {
    return <Snowflake className={className} />;
  }

  if (theme === "foggy") {
    return <CloudFog className={className} />;
  }

  return <Moon className={className} />;
}

export default function DashboardPage() {
  const [selectedLocation, setSelectedLocation] =
    useState<LocationItem>({
      name: "New Delhi",
      latitude: 28.6139,
      longitude: 77.209,
      country: "India",
      admin1: "Delhi",
    });

  const [weather, setWeather] =
    useState<WeatherResponse | null>(null);

  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  /*
   * Night is used as the initial value so that server-side
   * rendering and the first client render remain consistent.
   */
  const [videoBackground, setVideoBackground] =
    useState<VideoBackground>({
      period: "night",
      video: "/videos/Night.mp4",
    });

  // Select background video according to device time
  useEffect(() => {
    function updateBackgroundVideo() {
      const selectedVideo = getTimeBasedVideo(new Date());
      setVideoBackground(selectedVideo);
    }

    // Update immediately after page loads
    updateBackgroundVideo();

    // Check the time every minute
    const intervalId = window.setInterval(
      updateBackgroundVideo,
      60 * 1000
    );

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  // Load weather and alerts
  useEffect(() => {
    async function loadDashboardData() {
      setLoading(true);
      setError(null);

      try {
        const [weatherData, alertData] = await Promise.all([
          getWeather(
            selectedLocation.latitude,
            selectedLocation.longitude
          ),
          getAlerts(
            selectedLocation.latitude,
            selectedLocation.longitude
          ),
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

  const selectLocation = (location: LocationItem) => {
    setSelectedLocation(location);
  };

  /*
   * This type assertion prevents an error if weather_code and
   * is_day are not yet included in the WeatherResponse interface.
   */
  const currentWeather = weather?.current as
    | {
        weather_code?: number;
        is_day?: number;
      }
    | undefined;

  const weatherCode = currentWeather?.weather_code;

  // Use API day/night value if available.
  // Otherwise use the selected time period.
  const fallbackIsDay =
    videoBackground.period === "night" ? 0 : 1;

  const isDay =
    currentWeather?.is_day ?? fallbackIsDay;

  const weatherTheme = getWeatherTheme(
    weatherCode,
    isDay
  );

  // Derive risk factors dynamically
  const temperature =
    weather?.current?.temperature_2m ?? 28;

  const precipitation =
    weather?.current?.precipitation ?? 0;

  const windSpeed =
    weather?.current?.wind_speed_10m ?? 12;

  const floodScore = Math.min(
    100,
    Math.round(precipitation * 2.5 + 10)
  );

  const stormScore = Math.min(
    100,
    Math.round(
      windSpeed * 1.8 + precipitation * 0.5
    )
  );

  const heatScore = Math.min(
    100,
    Math.round((temperature / 45) * 100)
  );

  const windScore = Math.min(
    100,
    Math.round((windSpeed / 60) * 100)
  );

  return (
   <div className="video-full-width relative min-h-screen overflow-hidden bg-slate-900">
      {/* Time-based video background */}
      <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
        <video
          key={videoBackground.video}
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          aria-hidden="true"
          className="absolute inset-0 h-full w-full object-cover"
        >
          <source
            src={videoBackground.video}
            type="video/mp4"
          />
        </video>

        {/* Overlay for content readability */}
        <div
          className={`absolute inset-0 ${
            videoBackground.period === "night"
              ? "bg-slate-950/55"
              : videoBackground.period === "evening"
                ? "bg-slate-900/35"
                : videoBackground.period === "morning"
                  ? "bg-slate-900/20"
                  : "bg-white/15"
          }`}
        />

        {/* Bottom gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-slate-950/35" />
      </div>

      {/* Dashboard content */}
      <div className="relative z-10 mx-auto max-w-[1440px] space-y-6 p-4 sm:p-6">
        {/* Location header */}
<div className="glass-panel flex flex-col justify-between gap-6 rounded-xl p-6 md:flex-row md:items-center">
          <div className="space-y-1">
            <div className="flex items-center space-x-2 text-label-caps text-on-surface-variant">
              <MapPin className="h-4 w-4 text-primary" />
              <span>Target Location Telemetry</span>
            </div>

            <h1 className="flex flex-wrap items-center gap-2 text-headline-lg font-bold tracking-tight text-on-surface">
              <span>{selectedLocation.name}</span>

              {selectedLocation.country && (
                <span className="text-body-md font-normal text-on-surface-variant">
                  (
                  {selectedLocation.admin1
                    ? `${selectedLocation.admin1}, `
                    : ""}
                  {selectedLocation.country})
                </span>
              )}
            </h1>

            <p className="text-body-sm text-on-surface-variant">
              Real-time atmospheric telemetry, NWP forecast
              grids, and official IMD warnings.
            </p>

            <div className="flex flex-wrap items-center gap-2 pt-2">
              {!loading && weather && (
                <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">
                  <WeatherThemeIcon
                    theme={weatherTheme}
                    className="h-4 w-4"
                  />

                  <span>
                    {themeLabels[weatherTheme]}
                  </span>
                </div>
              )}

              {/* Time period badge */}
              <div className="inline-flex items-center rounded-full bg-black/45 px-3 py-1.5 text-xs font-semibold capitalize text-white backdrop-blur-md">
                {videoBackground.period} background
              </div>
            </div>
          </div>

          <div className="w-full shrink-0 md:w-80">
            <LocationSearch
              onSelectLocation={selectLocation}
              selectedLocation={selectedLocation}
            />
          </div>
        </div>

        {/* Active alerts */}
        <AlertBanner alerts={alerts} />

        {/* Loading, error or weather data */}
        {loading ? (
          <div className="space-y-6">
            <div className="flex h-64 items-center justify-center space-x-3 rounded-xl border border-white/40 bg-surface-container-low/90 text-body-sm text-on-surface-variant shadow-lg backdrop-blur-md">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />

              <span>
                Connecting to NWP telemetry & forecast
                engines...
              </span>
            </div>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-error/40 bg-error-container/90 p-6 text-body-sm text-on-error-container shadow-lg backdrop-blur-md">
            {error}
          </div>
        ) : weather ? (
          <>
            {/* Current weather */}
            <div className="glass-current rounded-xl">
  <WeatherMetricCard
    weather={weather}
    locationName={selectedLocation.name}
  />
</div>

            {/* Forecast */}
            <div className="glass-forecast rounded-xl">
  <ForecastStrip daily={weather.daily} />
</div>

            {/* Risk assessment */}
            <div className="glass-panel glass-risk space-y-3 rounded-xl p-4">
              <h2 className="flex items-center gap-2 text-headline-sm font-bold text-on-surface">
                <ShieldCheck className="h-5 w-5 text-primary" />
                <span>
                  Location Risk Assessment Grid
                </span>
              </h2>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <RiskFactorCard
                  label="Flood Risk"
                  value={`${floodScore}/100`}
                  percentage={floodScore}
                  severity={
                    floodScore >= 70
                      ? "critical"
                      : floodScore >= 40
                        ? "moderate"
                        : "low"
                  }
                  subtext="Evaluated against precipitation runoff metrics."
                />

                <RiskFactorCard
                  label="Storm Severity"
                  value={`${stormScore}/100`}
                  percentage={stormScore}
                  severity={
                    stormScore >= 70
                      ? "high"
                      : stormScore >= 40
                        ? "moderate"
                        : "low"
                  }
                  subtext="Based on wind gusts and convective potential."
                />

                <RiskFactorCard
                  label="Heat Index"
                  value={`${heatScore}/100`}
                  percentage={heatScore}
                  severity={
                    heatScore >= 75
                      ? "critical"
                      : heatScore >= 50
                        ? "high"
                        : "low"
                  }
                  subtext="Apparent thermal desiccation index."
                />

                <RiskFactorCard
                  label="Wind Damage"
                  value={`${windScore}/100`}
                  percentage={windScore}
                  severity={
                    windScore >= 60
                      ? "moderate"
                      : "low"
                  }
                  subtext="Structural wind strain calculation."
                />
              </div>
            </div>
          </>
        ) : null}

        {/* WeatherGPT CTA */}
        <div className="flex flex-col items-start justify-between gap-6 rounded-xl border border-primary/20 bg-primary-container/90 p-6 shadow-lg backdrop-blur-md sm:p-8 md:flex-row md:items-center">
          <div className="max-w-2xl space-y-2 text-on-primary-container">
            <div className="flex items-center space-x-2 text-label-caps font-bold">
              <Bot className="h-4 w-4" />
              <span>
                Natural Language Weather Intelligence
              </span>
            </div>

            <h2 className="text-headline-md font-bold tracking-tight">
              Have specific questions about local weather or
              agricultural timing?
            </h2>

            <p className="text-body-sm leading-relaxed opacity-90">
              Ask WeatherGPT in natural language (English,
              Hinglish, or Hindi) for grounded forecasts,
              travel safety guidelines, and crop spraying
              advice.
            </p>
          </div>

          <Link
            href="/chat"
            className="group flex shrink-0 items-center space-x-2 rounded-lg bg-primary px-6 py-3 text-body-sm font-bold text-on-primary shadow-md transition-all hover:bg-primary-container"
          >
            <span>Ask WeatherGPT AI</span>

            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </Link>
        </div>
      </div>
    </div>
  );
}