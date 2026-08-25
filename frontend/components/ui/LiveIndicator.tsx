"use client";

import React from "react";
import { Radio } from "lucide-react";

interface LiveIndicatorProps {
  status?: "connected" | "connecting" | "disconnected";
  label?: string;
  className?: string;
}

export default function LiveIndicator({
  status = "connected",
  label,
  className = "",
}: LiveIndicatorProps) {
  const isConnected = status === "connected";
  const isConnecting = status === "connecting";

  const defaultText = isConnected
    ? "LIVE WEBSOCKET CONNECTION"
    : isConnecting
    ? "CONNECTING FEED..."
    : "OFFLINE FEED";

  const colorStyle = isConnected
    ? "bg-emerald-50 text-emerald-800 border-emerald-300"
    : isConnecting
    ? "bg-amber-50 text-amber-800 border-amber-300"
    : "bg-red-50 text-red-800 border-red-300";

  const dotColor = isConnected
    ? "bg-emerald-500 animate-pulse"
    : isConnecting
    ? "bg-amber-500 animate-ping"
    : "bg-red-500";

  return (
    <span
      className={`inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full border text-[11px] font-mono font-bold tracking-wider ${colorStyle} ${className}`}
    >
      <span className={`w-2 h-2 rounded-full ${dotColor}`} />
      <span>{label || defaultText}</span>
    </span>
  );
}
