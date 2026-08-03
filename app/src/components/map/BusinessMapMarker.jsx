import L from "leaflet";
import { Marker } from "react-leaflet";

const VARIANTS = {
  candidate: { color: "#0A8F78", label: "음식점 후보", shape: "pin" },
  recommendation: { color: "#E15D47", label: "추천 음식점", shape: "pin" },
  inactive: { color: "#8B9690", label: "선택 제외", shape: "pin" },
  activityPrevious: { color: "#C27616", label: "이전 활동", shape: "dot" },
  activityCurrent: { color: "#087A5F", label: "선정 활동", shape: "dot" },
};

const iconCache = new Map();

function pinSvg(color, selected) {
  return `
    <svg width="${selected ? 40 : 34}" height="${selected ? 48 : 42}" viewBox="0 0 34 42" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" style="filter:drop-shadow(0 3px 3px rgba(23,33,29,.25))">
      ${selected ? '<circle cx="17" cy="16" r="15" fill="#FFFFFF" stroke="#075C45" stroke-width="2.5" opacity=".98"/>' : ""}
      <path d="M17 1C8.72 1 2 7.49 2 15.49c0 10.62 15 25.01 15 25.01s15-14.39 15-25.01C32 7.49 25.28 1 17 1Z" fill="${color}" stroke="#FFFFFF" stroke-width="2"/>
      <circle cx="17" cy="15.5" r="8.2" fill="#FFFFFF"/>
      <path d="M13.2 10.5v4.1c0 1.1.65 2 1.65 2.35V21M11.8 10.5v3.1M14.6 10.5v3.1M20.2 10.5v10.5M20.2 10.5c2.25 1.25 2.45 4.7 0 6.1" fill="none" stroke="${color}" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`;
}

function dotSvg(color, selected) {
  const size = selected ? 28 : 22;
  return `
    <svg width="${size}" height="${size}" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <circle cx="14" cy="14" r="${selected ? 12 : 9}" fill="#FFFFFF" stroke="${selected ? "#17211D" : color}" stroke-width="${selected ? 2 : 1.5}"/>
      <circle cx="14" cy="14" r="${selected ? 7 : 5.5}" fill="${color}"/>
    </svg>`;
}

function getBusinessMarkerIcon(variant = "candidate", selected = false) {
  const definition = VARIANTS[variant] ?? VARIANTS.candidate;
  const cacheKey = `${variant}:${selected}`;
  if (iconCache.has(cacheKey)) return iconCache.get(cacheKey);

  const isPin = definition.shape === "pin";
  const icon = L.divIcon({
    className: "business-map-marker",
    html: isPin ? pinSvg(definition.color, selected) : dotSvg(definition.color, selected),
    iconSize: isPin ? (selected ? [40, 48] : [34, 42]) : (selected ? [28, 28] : [22, 22]),
    iconAnchor: isPin ? (selected ? [20, 46] : [17, 40]) : (selected ? [14, 14] : [11, 11]),
    popupAnchor: isPin ? [0, -39] : [0, -12],
  });
  iconCache.set(cacheKey, icon);
  return icon;
}

function LegendSymbol({ variant }) {
  const definition = VARIANTS[variant] ?? VARIANTS.candidate;
  if (definition.shape === "dot") {
    return <span className="grid h-4 w-4 place-items-center rounded-full border border-white bg-white shadow-sm"><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: definition.color }} /></span>;
  }
  return <span className="relative block h-5 w-4"><span className="absolute left-0.5 top-0 h-3.5 w-3.5 rotate-45 rounded-[50%_50%_50%_0] border-2 border-white shadow-sm" style={{ backgroundColor: definition.color }} /></span>;
}

export function MapLegend({ items, className = "" }) {
  return (
    <div className={`rounded-xl border border-[#DDE4DF] bg-white/95 px-3 py-2 shadow-[0_4px_14px_rgba(23,33,29,0.12)] backdrop-blur ${className}`} aria-label="지도 범례">
      <p className="mb-1.5 text-[9px] font-black tracking-[0.12em] text-[#718078]">지도 범례</p>
      <div className="space-y-1.5">
        {items.map((item) => (
          <div key={`${item.variant}-${item.label}`} className="flex items-center gap-2 text-[10px] font-bold text-[#4F5D56]">
            <LegendSymbol variant={item.variant} />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BusinessMapMarker({ position, variant = "candidate", selected = false, eventHandlers, children }) {
  return (
    <Marker position={position} icon={getBusinessMarkerIcon(variant, selected)} eventHandlers={eventHandlers}>
      {children}
    </Marker>
  );
}

export default BusinessMapMarker;
