import { useEffect } from "react";
import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

function markerStyle(region, layer) {
  if (layer === "newcomers") {
    return { color: "#356A78", fillColor: "#74B6C8", value: region.newPowerReviewers ?? 0 };
  }
  if (layer === "supply") {
    const change = region.reviewSupplyChangeRate;
    return change === undefined
      ? { color: "#7FA894", fillColor: "#B7CFC2", value: region.reviewers }
      : change < 0
        ? { color: "#B4402F", fillColor: "#E86A54", value: Math.abs(change) * 100 }
        : { color: "#137A5A", fillColor: "#5DAE87", value: change * 100 };
  }
  if (region.highRiskRate >= 0.7) return { color: "#B4402F", fillColor: "#E15D47", value: region.highRiskRate * 100 };
  if (region.highRiskRate >= 0.6) return { color: "#A66A18", fillColor: "#DFA94A", value: region.highRiskRate * 100 };
  return { color: "#7FA894", fillColor: "#B7CFC2", value: region.highRiskRate * 100 };
}

function MapBounds({ regions }) {
  const map = useMap();
  const pointsKey = regions
    .map((region) => `${region.region}:${region.latitude}:${region.longitude}`)
    .join("|");
  useEffect(() => {
    const points = pointsKey.split("|").map((entry) => {
      const [, latitude, longitude] = entry.split(":");
      return [Number(latitude), Number(longitude)];
    });
    if (points.length > 1) map.fitBounds(points, { padding: [36, 36], maxZoom: 5 });
  }, [map, pointsKey]);
  return null;
}

function RegionalBubbleMap({
  regions,
  hoveredRegion,
  onHoverRegion,
  selectedRegion,
  onSelectRegion,
  layer = "highRisk",
}) {
  const mappedRegions = regions.filter(
    (region) => Number.isFinite(region.latitude) && Number.isFinite(region.longitude),
  );

  return (
    <div className="overflow-hidden rounded-xl border border-[#DDE4DF] bg-white p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 px-1 text-xs text-[#626D67]">
        <span>실제 지도 위에 대표 활동 도시를 표시합니다. 핀을 눌러 권역을 선택하세요.</span>
        <span>권역 집계 단위: state</span>
      </div>
      <MapContainer
        center={[39.5, -98.35]}
        zoom={4}
        scrollWheelZoom
        className="h-[360px] w-full rounded-lg"
        aria-label="권역별 리뷰 활동 지도"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapBounds regions={mappedRegions} />
        {mappedRegions.map((region) => {
          const style = markerStyle(region, layer);
          const selected = selectedRegion === region.region;
          const hovered = hoveredRegion === region.region;
          return (
            <CircleMarker
              key={region.region}
              center={[region.latitude, region.longitude]}
              radius={selected ? 13 : Math.max(7, Math.min(12, 6 + Math.sqrt(style.value || 0) / 3))}
              pathOptions={{
                color: selected || hovered ? "#17211D" : style.color,
                fillColor: style.fillColor,
                fillOpacity: selected ? 0.95 : 0.78,
                weight: selected || hovered ? 3 : 1.5,
              }}
              eventHandlers={{
                mouseover: () => onHoverRegion?.(region.region),
                mouseout: () => onHoverRegion?.(null),
                click: () => onSelectRegion?.(region.region),
              }}
            >
              {(selected || (layer === "supply" && region.reviewSupplyChangeRate < 0)) && (
                <Tooltip permanent direction="top" offset={[0, -10]} className="regional-map-label">
                  <span className="font-bold">{region.region}</span>{" "}
                  {region.reviewSupplyChangeRate !== undefined && `${region.reviewSupplyChangeRate >= 0 ? "+" : ""}${(region.reviewSupplyChangeRate * 100).toFixed(1)}%`}
                </Tooltip>
              )}
              <Popup>
                <strong>{region.region} 권역</strong><br />
                대표 활동 도시: {region.topCity}<br />
                활동 리뷰어: {region.reviewers.toLocaleString()}명<br />
                {layer === "supply" && region.reviewSupplyChangeRate !== undefined && (
                  <>전년 대비 리뷰 공급: {region.reviewSupplyChangeRate >= 0 ? "+" : ""}{(region.reviewSupplyChangeRate * 100).toFixed(1)}%</>
                )}
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}

export default RegionalBubbleMap;
