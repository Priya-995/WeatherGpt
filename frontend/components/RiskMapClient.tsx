"use client";

import { useState } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMapEvents } from "react-leaflet";
import L from "leaflet";

// Fix default leaflet marker icon asset URLs in Next.js
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

interface RiskMapClientProps {
  onLocationSelect: (lat: number, lon: number) => void;
  selectedLocation: { lat: number; lon: number } | null;
  riskLevel?: string;
}

function MapClickHandler({ onSelect }: { onSelect: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) {
      onSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

export default function RiskMapClient({
  onLocationSelect,
  selectedLocation,
  riskLevel = "low",
}: RiskMapClientProps) {
  const getCircleColor = (level: string) => {
    switch (level.toLowerCase()) {
      case "critical":
        return "#ef4444"; // red-500
      case "high":
        return "#f97316"; // orange-500
      case "moderate":
        return "#eab308"; // yellow-500
      default:
        return "#10b981"; // emerald-500
    }
  };

  return (
    <div className="rounded-xl overflow-hidden border border-slate-800 shadow-xl relative z-0">
      <MapContainer
        center={[20.5937, 78.9629]}
        zoom={5}
        scrollWheelZoom={true}
        style={{ height: "480px", width: "100%", zIndex: 0 }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapClickHandler onSelect={onLocationSelect} />

        {selectedLocation && (
          <CircleMarker
            center={[selectedLocation.lat, selectedLocation.lon]}
            radius={18}
            pathOptions={{
              color: getCircleColor(riskLevel),
              fillColor: getCircleColor(riskLevel),
              fillOpacity: 0.6,
              weight: 3,
            }}
          >
            <Popup>
              <div className="text-xs font-sans text-slate-900">
                <strong>Selected Coordinates:</strong>
                <br />
                Lat: {selectedLocation.lat.toFixed(4)}, Lon: {selectedLocation.lon.toFixed(4)}
                <br />
                <strong>Risk Level:</strong> {riskLevel.toUpperCase()}
              </div>
            </Popup>
          </CircleMarker>
        )}
      </MapContainer>
    </div>
  );
}
