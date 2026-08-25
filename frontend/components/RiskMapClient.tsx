"use client";

import { CircleMarker, MapContainer, Popup, TileLayer, useMapEvents } from "react-leaflet";
import L from "leaflet";

// Fix Leaflet default marker icons in Next.js
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
    const l = level.toLowerCase();
    if (l === "critical" || l === "severe" || l === "red") return "#ef4444"; // red-500
    if (l === "high" || l === "orange") return "#f97316"; // orange-500
    if (l === "moderate" || l === "medium" || l === "yellow") return "#f59e0b"; // amber-500
    return "#10b981"; // emerald-500
  };

  return (
    <div className="rounded-2xl overflow-hidden border border-slate-800 shadow-2xl relative z-0">
      <MapContainer
        center={[20.5937, 78.9629]}
        zoom={5}
        scrollWheelZoom={true}
        style={{ height: "500px", width: "100%", zIndex: 0 }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapClickHandler onSelect={onLocationSelect} />

        {selectedLocation && (
          <CircleMarker
            center={[selectedLocation.lat, selectedLocation.lon]}
            radius={22}
            pathOptions={{
              color: getCircleColor(riskLevel),
              fillColor: getCircleColor(riskLevel),
              fillOpacity: 0.6,
              weight: 4,
            }}
          >
            <Popup>
              <div className="text-xs font-sans text-slate-900 p-1 space-y-1">
                <div className="font-bold border-b pb-1">Coordinates Inspected</div>
                <div>Lat: {selectedLocation.lat.toFixed(4)}°</div>
                <div>Lon: {selectedLocation.lon.toFixed(4)}°</div>
                <div className="font-bold pt-1 uppercase" style={{ color: getCircleColor(riskLevel) }}>
                  Risk Index: {riskLevel.toUpperCase()}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        )}
      </MapContainer>
    </div>
  );
}
