import { useEffect, useMemo, useState } from "react";
import L from "leaflet";
import {
  Circle,
  CircleMarker,
  GeoJSON,
  MapContainer,
  Marker,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

import regionBoundariesUrl from "../../assets/maps/yelp-regions-admin1.geojson?url";

const SUPPLY_COLORS = {
  strong_decline: "#D95742",
  decline: "#EE8D75",
  stable: "#D8DCD7",
  growth: "#8BC8B0",
  strong_growth: "#238764",
  insufficient: "#AEB7B1",
};

const SELECTED_CITY_ICON = L.divIcon({
  className: "selected-region-pin",
  html: '<span class="selected-region-pin__marker"><span class="selected-region-pin__dot"></span></span>',
  iconSize: [40, 50],
  iconAnchor: [20, 46],
});

const LEGENDS = {
  supply: [
    ["큰 폭 감소 · -15% 이하", SUPPLY_COLORS.strong_decline],
    ["감소 · -15% ~ -5%", SUPPLY_COLORS.decline],
    ["보합 · -5% ~ +5%", SUPPLY_COLORS.stable],
    ["증가 · +5% ~ +15%", SUPPLY_COLORS.growth],
    ["큰 폭 증가 · +15% 이상", SUPPLY_COLORS.strong_growth],
  ],
  core: [
    ["집중 관리 · CRM 20명 이상", "#075C45"],
    ["검토 필요 · CRM 5~19명", "#3E9675"],
    ["관찰 · CRM 1~4명", "#9CCDB8"],
    ["배정 없음", "#D8DCD7"],
  ],
  newcomers: [
    ["유입 감소", "#E0715A"],
    ["비교 보합", "#D8DCD7"],
    ["유입 증가", "#319171"],
    ["전년 비교 불가", "#AEB7B1"],
  ],
};

const RANK_LABELS = {
  supply: "공급 위험 순",
  core: "통합 대상 순",
  newcomers: "신규 유입 순",
};

function displayCity(value) {
  return value
    .toLocaleLowerCase("en-US")
    .replace(/(^|[\s'-])[a-z]/g, (letter) => letter.toLocaleUpperCase("en-US"));
}

function signedPercent(value) {
  if (value === null || value === undefined) return "비교 불가";
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)}%`;
}

function cityColor(city, layer) {
  if (!city.minimumSampleMet) return SUPPLY_COLORS.insufficient;
  if (layer === "core") {
    if (city.crmTargets >= 20) return "#075C45";
    if (city.crmTargets >= 5) return "#3E9675";
    if (city.crmTargets >= 1) return "#9CCDB8";
    return "#D8DCD7";
  }
  if (layer === "newcomers") {
    const rate = city.newPowerReviewerChangeRate;
    if (rate === null || rate === undefined) return "#AEB7B1";
    if (rate < -0.05) return "#E0715A";
    if (rate > 0.05) return "#319171";
    return "#D8DCD7";
  }
  return SUPPLY_COLORS[city.supplyStatus] ?? SUPPLY_COLORS.insufficient;
}

function markerRadius(city) {
  if (!city.minimumSampleMet) return 2.5;
  if (city.supplyVolumeBand === "large") return 8;
  if (city.supplyVolumeBand === "medium") return 6;
  return 4.5;
}

function MapViewport({ scope, selectedCity, regionPositions }) {
  const map = useMap();
  useEffect(() => {
    if (scope === "region") {
      if (regionPositions.length === 1) {
        map.setView(regionPositions[0], 8, { animate: false });
      } else if (regionPositions.length > 1) {
        map.fitBounds(L.latLngBounds(regionPositions), {
          animate: false,
          maxZoom: 7,
          padding: [54, 54],
        });
      }
      return;
    }
    if (!selectedCity) return;
    const radiusKm = selectedCity.displayRadiusKm;
    const latitudeDelta = radiusKm / 111.195;
    const longitudeDelta = radiusKm
      / (111.195 * Math.cos((selectedCity.latitude * Math.PI) / 180));
    map.fitBounds(
      [
        [selectedCity.latitude - latitudeDelta, selectedCity.longitude - longitudeDelta],
        [selectedCity.latitude + latitudeDelta, selectedCity.longitude + longitudeDelta],
      ],
      { animate: false, maxZoom: 11, padding: [38, 38] },
    );
  }, [map, regionPositions, scope, selectedCity]);
  return null;
}

function CityTooltip({ city, layer }) {
  const layerValue = layer === "core"
    ? `통합 검토 대상 ${city.crmTargets.toLocaleString()}명`
    : layer === "newcomers"
      ? `신규 핵심 ${city.newPowerReviewers.toLocaleString()}명 · 전년 ${signedPercent(city.newPowerReviewerChangeRate)}`
      : `리뷰 공급 ${signedPercent(city.reviewSupplyChangeRate)}`;
  return (
    <div className="grid min-w-44 gap-1">
      <strong>{city.state} · {displayCity(city.city)}</strong>
      <span>{layerValue}</span>
      <span>리뷰 {city.reviewCount.toLocaleString()}건 · 활동 리뷰어 {city.activeReviewers.toLocaleString()}명</span>
      {!city.minimumSampleMet && <span className="font-bold text-[#9A594C]">운영 표본 기준 미달</span>}
    </div>
  );
}

function rankValue(city, layer) {
  if (layer === "core") return `통합 ${city.crmTargets.toLocaleString()}명`;
  if (layer === "newcomers") return `신규 ${city.newPowerReviewers.toLocaleString()}명`;
  return `공급 ${signedPercent(city.reviewSupplyChangeRate)}`;
}

function SupplyOverviewMap({
  cities,
  regions,
  layer,
  scope,
  selectedRegion,
  selectedCity,
  rankPosition,
  rankTotal,
  onSelectRegion,
  onSelectCity,
  onSetScope,
  onRankOffset,
  onFirstRank,
}) {
  const [boundaries, setBoundaries] = useState(null);
  const [boundaryError, setBoundaryError] = useState(false);
  const eligibleCities = useMemo(
    () => cities.filter((city) => city.minimumSampleMet),
    [cities],
  );
  const selectedRegionCode = selectedRegion?.region ?? selectedCity?.state;
  const regionCities = useMemo(
    () => eligibleCities.filter((city) => city.state === selectedRegionCode),
    [eligibleCities, selectedRegionCode],
  );
  const regionPositions = useMemo(
    () => regionCities.map((city) => [city.latitude, city.longitude]),
    [regionCities],
  );
  const rankField = layer === "core"
    ? "coreReviewerRank"
    : layer === "newcomers"
      ? "newcomerRank"
      : "supplyRank";
  const sortedRegionCities = useMemo(
    () => [...regionCities].sort((first, second) => first[rankField] - second[rankField]),
    [rankField, regionCities],
  );

  useEffect(() => {
    let cancelled = false;
    fetch(regionBoundariesUrl)
      .then((response) => {
        if (!response.ok) throw new Error("권역 경계를 불러오지 못했습니다.");
        return response.json();
      })
      .then((data) => { if (!cancelled) setBoundaries(data); })
      .catch(() => { if (!cancelled) setBoundaryError(true); });
    return () => { cancelled = true; };
  }, []);

  if (boundaryError) return <div className="grid h-[430px] place-items-center rounded-xl bg-[#F4F6F3] text-sm text-[#718078]">도시 지도를 표시할 수 없습니다.</div>;
  if (!boundaries || !selectedCity || !selectedRegion) return <div className="h-[430px] animate-pulse rounded-xl bg-[#EDF1EE]" aria-label="도시 지도를 불러오는 중" />;

  const selectedValue = scope === "city" ? `${selectedCity.state}|${selectedCity.cityKey}` : "";
  const visibleCities = scope === "region" ? regionCities : cities;

  return (
    <div className="relative isolate z-0 overflow-hidden rounded-xl border border-[#DDE4DF] bg-[#EAF1EE]">
      <MapContainer center={[selectedCity.latitude, selectedCity.longitude]} zoom={9} zoomSnap={0.25} scrollWheelZoom className="h-[430px] w-full" aria-label="도시별 리뷰 공급 지도">
        <TileLayer className="city-map-tiles" attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <MapViewport scope={scope} selectedCity={selectedCity} regionPositions={regionPositions} />
        <GeoJSON
          key={`${selectedRegionCode}-${scope}`}
          data={boundaries}
          interactive={false}
          style={(feature) => ({
            color: feature.properties.region === selectedRegionCode ? "#2E8066" : "#AAB5AF",
            fillColor: feature.properties.region === selectedRegionCode ? "#8BC8B0" : "#FFFFFF",
            fillOpacity: feature.properties.region === selectedRegionCode && scope === "region" ? 0.12 : 0,
            weight: feature.properties.region === selectedRegionCode ? 2.4 : 0.55,
            dashArray: feature.properties.region === selectedRegionCode ? null : "3 5",
          })}
        />
        {scope === "city" && (
          <Circle
            center={[selectedCity.latitude, selectedCity.longitude]}
            radius={selectedCity.displayRadiusKm * 1000}
            pathOptions={{ color: "#087454", weight: 2, dashArray: "7 7", fillColor: "#75B79C", fillOpacity: 0.07 }}
            interactive={false}
          />
        )}
        {visibleCities.map((city) => (
          <CircleMarker
            key={`${city.state}-${city.cityKey}`}
            center={[city.latitude, city.longitude]}
            radius={markerRadius(city)}
            pathOptions={{
              color: scope === "city" && city === selectedCity ? "#17211D" : "#FFFFFF",
              weight: scope === "city" && city === selectedCity ? 3 : city.minimumSampleMet ? 1.5 : 1,
              fillColor: cityColor(city, layer),
              fillOpacity: city.minimumSampleMet ? 0.96 : 0.65,
            }}
            eventHandlers={{ click: () => onSelectCity(city) }}
          >
            <Tooltip direction="top" offset={[0, -5]} className="operation-region-tooltip"><CityTooltip city={city} layer={layer} /></Tooltip>
          </CircleMarker>
        ))}
        {scope === "city" && (
          <Marker position={[selectedCity.latitude, selectedCity.longitude]} icon={SELECTED_CITY_ICON} zIndexOffset={1000}>
            <Tooltip permanent direction="bottom" offset={[0, 4]} className="selected-region-label">{selectedCity.state} · {displayCity(selectedCity.city)}</Tooltip>
          </Marker>
        )}
      </MapContainer>

      <div
        className="absolute left-3 top-3 z-[600] grid max-w-[calc(100%-190px)] items-center gap-1.5 rounded-lg border border-[#D5DED8] bg-white/96 p-1.5 shadow-lg"
        style={{ gridTemplateColumns: "80px 250px 115px 28px 28px 60px" }}
      >
        <label className="sr-only" htmlFor="region-map-selector">권역 선택</label>
        <select id="region-map-selector" value={selectedRegionCode} onChange={(event) => onSelectRegion(regions.find((region) => region.region === event.target.value))} className="min-h-8 w-20 rounded-md border-0 bg-[#F3F7F4] px-2 text-[11px] font-black text-[#075C45] outline-none focus:ring-2 focus:ring-[#087454]">
          {regions.map((region) => <option key={region.region} value={region.region}>{region.region}</option>)}
        </select>
        <label className="sr-only" htmlFor="city-map-selector">리뷰 활동 도시 선택</label>
        <select
          id="city-map-selector"
          value={selectedValue}
          onChange={(event) => {
            if (!event.target.value) {
              onSetScope("region");
              return;
            }
            const [state, cityKey] = event.target.value.split("|");
            const city = regionCities.find((item) => item.state === state && item.cityKey === cityKey);
            if (city) onSelectCity(city);
          }}
          className="min-h-8 w-[250px] min-w-0 rounded-md border-0 bg-white px-2 text-[11px] font-bold text-[#26332D] outline-none focus:ring-2 focus:ring-[#087454]"
        >
          <option value="">{selectedRegionCode} 권역 전체 보기</option>
          {sortedRegionCities.map((city) => <option key={city.cityKey} value={`${city.state}|${city.cityKey}`}>{city[rankField]}위 · {displayCity(city.city)} · {rankValue(city, layer)}</option>)}
        </select>
        <span className="w-[115px] whitespace-nowrap border-l border-[#DDE4DF] pl-2 text-[9px] font-bold text-[#526159]">{RANK_LABELS[layer]} {rankPosition ?? "—"}/{rankTotal}</span>
        <button type="button" onClick={() => onRankOffset(-1)} disabled={!rankPosition || rankPosition <= 1} className="grid h-7 w-7 shrink-0 place-items-center rounded border border-[#DDE4DF] text-xs font-black text-[#526159] disabled:opacity-30" aria-label="이전 순위">‹</button>
        <button type="button" onClick={() => onRankOffset(1)} disabled={!rankPosition || rankPosition >= rankTotal} className="grid h-7 w-7 shrink-0 place-items-center rounded border border-[#DDE4DF] text-xs font-black text-[#526159] disabled:opacity-30" aria-label="다음 순위">›</button>
        <button type="button" onClick={onFirstRank} className="min-h-7 w-[60px] shrink-0 whitespace-nowrap rounded border border-[#9CCDB8] px-1 text-[9px] font-black text-[#075C45]">1위 보기</button>
      </div>

      <div className="absolute right-3 top-3 z-[600] flex rounded-lg border border-[#D5DED8] bg-white/96 p-1 shadow-lg">
        <button type="button" onClick={() => onSetScope("city")} className={`min-h-8 rounded-md px-3 text-[10px] font-bold ${scope === "city" ? "bg-[#075C45] text-white" : "text-[#526159] hover:bg-[#F2F6F3]"}`}>도시 상세</button>
        <button type="button" onClick={() => onSetScope("region")} className={`min-h-8 rounded-md px-3 text-[10px] font-bold ${scope === "region" ? "bg-[#075C45] text-white" : "text-[#526159] hover:bg-[#F2F6F3]"}`}>권역 요약</button>
      </div>

      <div className="pointer-events-none absolute bottom-4 left-4 z-[500] w-52 rounded-xl border border-[#DDE4DF] bg-white/95 p-3 shadow-lg">
        <p className="text-[10px] font-black tracking-[0.12em] text-[#526159]">도시 상태 범례</p>
        <div className="mt-2 space-y-1.5">
          {LEGENDS[layer].map(([label, color]) => <div key={label} className="flex items-center gap-2 text-[10px] text-[#526159]"><span className="h-3 w-3 rounded-full border border-white shadow-[0_0_0_1px_rgba(23,33,29,.15)]" style={{ backgroundColor: color }} />{label}</div>)}
          <div className="mt-2 flex items-center gap-2 border-t border-[#E5E9E6] pt-2 text-[9px] text-[#718078]"><span className={`block w-8 border-t-2 ${scope === "city" ? "border-dashed border-[#087454]" : "border-[#2E8066]"}`} />{scope === "city" ? "선택 도시 활동 반경" : "선택 권역 경계"}</div>
        </div>
      </div>
    </div>
  );
}

export default SupplyOverviewMap;
