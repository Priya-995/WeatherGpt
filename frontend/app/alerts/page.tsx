"use client";

import { useEffect, useState } from "react";
import { Alert, getAlertWebSocketUrl, getAlerts } from "@/lib/api";

const formatAlertType = (typeStr: string): string => {
  if (!typeStr) return "Weather Warning";
  const cleaned = typeStr.toLowerCase().replace(/_/g, " ");
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1) + " Warning";
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");
  const [liveNotification, setLiveNotification] = useState<string | null>(null);

  // Fetch initial alerts
  useEffect(() => {
    async function loadAlerts() {
      try {
        const res = await getAlerts();
        setAlerts(res.alerts || []);
      } catch {
        setError("Unable to load active weather alerts right now. Please check your connection and try again.");
      } finally {
        setLoading(false);
      }
    }
    loadAlerts();
  }, []);

  // WebSocket Live Subscription
  useEffect(() => {
    const wsUrl = getAlertWebSocketUrl();
    let ws: WebSocket | null = null;

    try {
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsStatus("connected");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === "new_alert" && data.alert) {
            const newAlert: Alert = data.alert;
            setAlerts((prev) => [newAlert, ...prev.filter((a) => a.id !== newAlert.id)]);
            setLiveNotification(`New Warning Issued for ${newAlert.affected_location}`);
            setTimeout(() => setLiveNotification(null), 5000);
          }
        } catch {
          // ignore non-json
        }
      };

      ws.onerror = () => {
        setWsStatus("disconnected");
      };

      ws.onclose = () => {
        setWsStatus("disconnected");
      };
    } catch {
      setWsStatus("disconnected");
    }

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const getSeverityBadge = (severity: string) => {
    const sev = (severity || "").toLowerCase();
    if (sev === "red" || sev === "severe" || sev === "extreme" || sev === "high") {
      return "bg-red-500/20 text-red-300 border-red-500/40";
    }
    if (sev === "orange" || sev === "moderate" || sev === "medium") {
      return "bg-amber-500/20 text-amber-300 border-amber-500/40";
    }
    return "bg-yellow-500/20 text-yellow-300 border-yellow-500/40";
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-slate-900/60 p-6 rounded-xl border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <span>🚨</span> Weather Alert Center
          </h1>
          <p className="text-sm text-slate-400">
            Real-time emergency warnings and public safety bulletins.
          </p>
        </div>

        {/* Live WebSocket Status Indicator */}
        <div className="flex items-center space-x-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              wsStatus === "connected"
                ? "bg-emerald-500 animate-pulse"
                : wsStatus === "connecting"
                ? "bg-amber-500"
                : "bg-red-500"
            }`}
          />
          <span className="text-slate-300 font-medium">
            {wsStatus === "connected"
              ? "Live Feed Active"
              : wsStatus === "connecting"
              ? "Connecting to Feed..."
              : "Feed Offline"}
          </span>
        </div>
      </div>

      {/* Toast Notification for Realtime Alert */}
      {liveNotification && (
        <div className="bg-gradient-to-r from-red-600 to-amber-600 text-white p-3 rounded-lg shadow-xl text-sm font-semibold flex items-center justify-between animate-bounce">
          <span>⚡ LIVE WARNING: {liveNotification}</span>
        </div>
      )}

      {/* Active Alerts List */}
      {loading ? (
        <div className="h-48 flex items-center justify-center bg-slate-900/40 rounded-xl border border-slate-800">
          <div className="text-slate-400 text-sm flex items-center space-x-2">
            <div className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
            <span>Loading active weather alerts...</span>
          </div>
        </div>
      ) : error ? (
        <div className="p-4 bg-red-900/30 border border-red-800 rounded-xl text-red-300 text-sm">
          {error}
        </div>
      ) : alerts.length === 0 ? (
        <div className="p-8 text-center bg-slate-900/40 rounded-xl border border-slate-800 text-slate-400 text-sm">
          No active weather warnings at this moment.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="bg-slate-900/80 p-5 rounded-xl border border-slate-800 hover:border-slate-700 transition-colors space-y-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                <div className="flex items-center space-x-2">
                  <span
                    className={`text-xs uppercase font-extrabold px-2.5 py-1 rounded border ${getSeverityBadge(
                      alert.severity
                    )}`}
                  >
                    {alert.severity ? alert.severity.toUpperCase() : "WARNING"}
                  </span>
                  <span className="text-xs font-semibold text-slate-300 bg-slate-950 px-2.5 py-0.5 rounded border border-slate-800">
                    {formatAlertType(alert.alert_type)}
                  </span>
                </div>
                <div className="text-xs text-slate-400">
                  Issued by: {alert.source || "Meteorological Department"}
                </div>
              </div>

              <div>
                <h3 className="text-base font-bold text-white">{alert.affected_location}</h3>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">{alert.instructions}</p>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400 pt-2 border-t border-slate-800/50">
                <div>
                  Issued: {new Date(alert.issue_time).toLocaleString()}
                </div>
                <div className="text-amber-400 font-medium">
                  Valid Until: {new Date(alert.expiry_time).toLocaleString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
