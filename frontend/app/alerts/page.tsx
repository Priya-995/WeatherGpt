"use client";

import { useEffect, useState } from "react";
import { Alert, LocationItem, INDIAN_STATES, getAlertWebSocketUrl, getAlerts } from "@/lib/api";
import AlertCard from "@/components/ui/AlertCard";
import LiveIndicator from "@/components/ui/LiveIndicator";
import LocationSearch from "@/components/ui/LocationSearch";
import { normalizeSeverity } from "@/components/ui/SeverityBadge";
import {
  AlertTriangle,
  RefreshCw,
  Filter,
  ArrowUpDown,
  MapPin,
  CheckCircle2,
  BellRing,
  Globe2,
  Search,
} from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");
  const [liveNotification, setLiveNotification] = useState<string | null>(null);
  const [activeSeverity, setActiveSeverity] = useState<string>("all");
  const [sortOrder, setSortOrder] = useState<"newest" | "severity">("severity");

  // "subdivision" -> Filter by Indian State/Subdivision (e.g. Uttar Pradesh, Maharashtra, All India)
  // "district"    -> Filter by specific district name & state (IMD District-wise GIS warnings)
  // "location"    -> Filter to specific coordinates via location search & point-in-polygon
  const [scope, setScope] = useState<"subdivision" | "district" | "location">("subdivision");
  const [selectedState, setSelectedState] = useState<string>("All India");
  const [districtQuery, setDistrictQuery] = useState<string>("");
  const [selectedLocation, setSelectedLocation] = useState<LocationItem>({
    name: "Lucknow",
    latitude: 26.8467,
    longitude: 80.9462,
    country: "India",
    admin1: "Uttar Pradesh",
  });

  const fetchAlertsData = async () => {
    setError(null);
    try {
      let res;
      if (scope === "location") {
        res = await getAlerts(selectedLocation.latitude, selectedLocation.longitude);
      } else if (scope === "district") {
        res = await getAlerts(undefined, undefined, selectedState, districtQuery);
      } else {
        res = await getAlerts(undefined, undefined, selectedState);
      }

      if (res.error) {
        setError("Couldn't reach alert service");
        setAlerts([]);
      } else {
        setError(null);
        setAlerts(res.alerts || []);
      }
    } catch (err) {
      console.error("Unexpected error in fetchAlertsData:", err);
      setError("Couldn't reach alert service");
    } finally {
      setLoading(false);
    }
  };

  // Re-fetch whenever scope, location, selectedState, or districtQuery changes
  useEffect(() => {
    setLoading(true);
    fetchAlertsData();

    const pollId = setInterval(fetchAlertsData, 90_000);
    return () => clearInterval(pollId);
  }, [scope, selectedLocation, selectedState, districtQuery]);

  const handleRefreshFeed = async () => {
    setRefreshing(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/alerts/refresh`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.alerts || []);
      }
    } catch {
      await fetchAlertsData();
    } finally {
      setRefreshing(false);
    }
  };

  // WebSocket Live Subscription
  useEffect(() => {
    const wsUrl = getAlertWebSocketUrl();
    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => setWsStatus("connected");
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === "connected" && Array.isArray(data.active_alerts) && data.active_alerts.length > 0) {
            setAlerts((prev) => (prev.length === 0 ? data.active_alerts : prev));
          } else if (data.event === "new_alert" && data.alert) {
            const newAlert: Alert = data.alert;
            setAlerts((prev) => [newAlert, ...prev.filter((a) => a.id !== newAlert.id)]);
            setLiveNotification(`New Live Alert Issued: ${newAlert.affected_location || 'Emergency Region'}`);
            setTimeout(() => setLiveNotification(null), 6000);
          }
        } catch {
          // ignore non-json
        }
      };

      ws.onerror = () => setWsStatus("disconnected");
      ws.onclose = () => setWsStatus("disconnected");
    } catch {
      setWsStatus("disconnected");
    }

    return () => {
      if (ws) ws.close();
    };
  }, []);

  // Filter & Sort Logic
  const filteredAlerts = alerts.filter((a) => {
    if (activeSeverity === "all") return true;
    return normalizeSeverity(a.severity) === activeSeverity;
  });

  const sortedAlerts = [...filteredAlerts].sort((a, b) => {
    if (sortOrder === "severity") {
      const rank: Record<string, number> = { critical: 4, high: 3, moderate: 2, low: 1 };
      return (rank[normalizeSeverity(b.severity)] || 0) - (rank[normalizeSeverity(a.severity)] || 0);
    }
    return new Date(b.issue_time).getTime() - new Date(a.issue_time).getTime();
  });

  return (
    <div className="space-y-6 max-w-[1440px] mx-auto">
      {/* Top Header & Live Indicator */}
      <div className="bg-surface-container-lowest p-6 rounded-xl border border-surface-container-high shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-error-container text-on-error-container rounded-lg">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <h1 className="text-headline-lg font-bold text-on-surface tracking-tight">
              Official Alert Center
            </h1>
          </div>
          <p className="text-body-sm text-on-surface-variant">
            Emergency weather warnings issued by IMD & disaster management authority.
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <button
            type="button"
            onClick={handleRefreshFeed}
            disabled={refreshing}
            className="text-body-sm font-semibold bg-surface-container hover:bg-surface-container-high text-on-surface px-3.5 py-2 rounded-lg border border-outline-variant/40 transition-colors flex items-center space-x-1.5"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
            <span>{refreshing ? "Refreshing..." : "Refresh Feed"}</span>
          </button>

          <LiveIndicator status={wsStatus} />
        </div>
      </div>

      {/* Live Notification Toast */}
      {liveNotification && (
        <div className="bg-error-container text-on-error-container p-4 rounded-xl shadow-md text-body-sm font-bold flex items-center justify-between animate-bounce border border-error/30">
          <div className="flex items-center space-x-2">
            <BellRing className="w-4 h-4 text-error animate-pulse" />
            <span>⚡ EMERGENCY REAL-TIME ALERT: {liveNotification}</span>
          </div>
        </div>
      )}

      {/* Scope & State / District Selector Controls */}
      <div className="flex flex-col gap-4 bg-surface-container-low p-4 rounded-xl border border-surface-container-high">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-label-caps text-on-surface-variant font-bold flex items-center gap-1">
              <Globe2 className="w-3.5 h-3.5" /> Warning Feed Mode:
            </span>
            {[
              { id: "subdivision", label: "Subdivision / State" },
              { id: "district", label: "District-wise Warnings (GIS)" },
              { id: "location", label: "Location Coordinates" },
            ].map((mode) => (
              <button
                key={mode.id}
                type="button"
                onClick={() => setScope(mode.id as any)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase transition-all ${
                  scope === mode.id
                    ? "bg-primary text-on-primary shadow-sm"
                    : "bg-surface-container-lowest text-on-surface-variant hover:text-on-surface border border-outline-variant/30"
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>
        </div>

        {/* Dynamic Controls Row */}
        <div className="pt-2 border-t border-surface-container-high/60 flex flex-wrap items-center gap-3">
          {(scope === "subdivision" || scope === "district") && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-on-surface-variant">State:</span>
              <select
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                className="bg-surface-container-lowest border border-outline-variant/50 rounded-lg px-3 py-1.5 text-xs font-semibold text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                {INDIAN_STATES.map((st) => (
                  <option key={st} value={st}>
                    {st}
                  </option>
                ))}
              </select>
            </div>
          )}

          {scope === "district" && (
            <div className="flex items-center gap-2 flex-1 min-w-[240px]">
              <span className="text-xs font-bold text-on-surface-variant shrink-0">District:</span>
              <div className="relative flex-1">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-on-surface-variant/60" />
                <input
                  type="text"
                  placeholder="Search district e.g. Belgaum, Thane, Lucknow, Thrissur, Sagar..."
                  value={districtQuery}
                  onChange={(e) => setDistrictQuery(e.target.value)}
                  className="w-full bg-surface-container-lowest border border-outline-variant/50 rounded-lg pl-8 pr-3 py-1.5 text-xs font-semibold text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>
              {districtQuery && (
                <button
                  type="button"
                  onClick={() => setDistrictQuery("")}
                  className="text-xs text-on-surface-variant hover:text-on-surface px-2 py-1 font-semibold"
                >
                  Clear
                </button>
              )}
            </div>
          )}

          {scope === "location" && (
            <div className="flex-1 flex flex-col sm:flex-row sm:items-center gap-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-on-surface bg-surface-container-lowest px-2.5 py-1.5 rounded-lg border border-outline-variant/40 shrink-0">
                <MapPin className="w-3.5 h-3.5 text-primary" />
                <span>
                  {selectedLocation.name}
                  {selectedLocation.admin1 ? `, ${selectedLocation.admin1}` : ""}
                </span>
              </div>
              <LocationSearch
                selectedLocation={selectedLocation}
                onSelectLocation={setSelectedLocation}
                className="sm:max-w-xs"
              />
            </div>
          )}
        </div>
      </div>

      {/* Region Status Banner */}
      {!loading && !error && scope !== "location" && (
        <div
          className={`p-4 rounded-xl border text-body-sm font-bold flex items-center justify-between shadow-xs transition-all ${
            sortedAlerts.length > 0
              ? "bg-error-container/20 border-error/40 text-on-surface"
              : "bg-emerald-50 border-emerald-200 text-emerald-900"
          }`}
        >
          <div className="flex items-center gap-2.5">
            {sortedAlerts.length > 0 ? (
              <>
                <AlertTriangle className="w-5 h-5 text-error shrink-0" />
                <div>
                  <span className="font-extrabold text-error">
                    ALERT: {districtQuery ? `District '${districtQuery}'` : selectedState} has Active Warnings
                  </span>
                  <p className="text-xs font-normal text-on-surface-variant">
                    IMD has issued {sortedAlerts.length} active emergency warning(s) covering {districtQuery ? `district '${districtQuery}'` : selectedState}.
                  </p>
                </div>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                <div>
                  <span className="font-bold text-emerald-900">
                    NOMINAL: No Active Weather Warnings for {districtQuery ? `District '${districtQuery}'` : selectedState}
                  </span>
                  <p className="text-xs font-normal text-emerald-700">
                    Official IMD GIS feed reports zero active emergency warnings for {districtQuery ? `district '${districtQuery}'` : selectedState} at this time.
                  </p>
                </div>
              </>
            )}
          </div>
          <span className="text-xs font-mono font-bold px-2.5 py-1 bg-white/80 rounded border border-current/20 shrink-0">
            {sortedAlerts.length} Warning(s)
          </span>
        </div>
      )}

      {/* Filter Bar & Sort Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-surface-container-low p-4 rounded-xl border border-surface-container-high">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-label-caps text-on-surface-variant font-bold flex items-center gap-1">
            <Filter className="w-3.5 h-3.5" /> Severity Filter:
          </span>
          {["all", "critical", "high", "moderate", "low"].map((sev) => (
            <button
              key={sev}
              type="button"
              onClick={() => setActiveSeverity(sev)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase transition-all ${
                activeSeverity === sev
                  ? "bg-primary text-on-primary shadow-sm"
                  : "bg-surface-container-lowest text-on-surface-variant hover:text-on-surface border border-outline-variant/30"
              }`}
            >
              {sev}
            </button>
          ))}
        </div>

        <div className="flex items-center space-x-2 text-xs text-on-surface-variant font-medium">
          <ArrowUpDown className="w-3.5 h-3.5 text-outline" />
          <span>Sort:</span>
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as any)}
            className="bg-surface-container-lowest border border-outline-variant/40 rounded-lg px-2.5 py-1 text-xs text-on-surface focus:outline-none"
          >
            <option value="severity">Highest Severity First</option>
            <option value="newest">Most Recent First</option>
          </select>
        </div>
      </div>

      {/* Main Content: Bento Alert Cards (Full Width) */}
      <div className="w-full space-y-4">
        {loading ? (
          <div className="h-64 flex flex-col items-center justify-center bg-surface-container-low rounded-xl border border-surface-container-high space-y-3 text-on-surface-variant text-body-sm">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span>
              {scope === "district"
                ? `Fetching alerts for ${selectedLocation.name}...`
                : `Fetching live IMD alerts for ${selectedState}...`}
            </span>
          </div>
        ) : error ? (
          <div className="p-6 bg-warning-container/40 text-on-surface rounded-xl border border-warning/40 text-body-sm space-y-2">
            <div className="flex items-center gap-2 font-bold text-warning">
              <AlertTriangle className="w-4 h-4" />
              <span>Live Feed Temporarily Unavailable</span>
            </div>
            <p className="text-on-surface-variant text-xs">{error}</p>
            <p className="text-xs text-outline">
              The IMD CAP feed could not be reached. No warnings are being shown because we
              will not display fabricated data — check back shortly or use the Refresh button.
            </p>
          </div>
        ) : sortedAlerts.length === 0 ? (
          <div className="p-12 text-center bg-surface-container-lowest rounded-xl border border-surface-container-high text-on-surface-variant text-body-sm space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
            <div className="font-bold text-on-surface">
              {scope === "district"
                ? `No active warnings for ${selectedLocation.name}${
                    selectedLocation.admin1 ? `, ${selectedLocation.admin1}` : ""
                  }`
                : `No active alerts for ${selectedState}`}
            </div>
            <p className="text-xs text-outline">
              The live IMD feed returned zero active alerts for {scope === "district" ? selectedLocation.name : selectedState}. Conditions are nominal.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sortedAlerts.map((alert, idx) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                featured={idx === 0 && normalizeSeverity(alert.severity) === "critical"}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}