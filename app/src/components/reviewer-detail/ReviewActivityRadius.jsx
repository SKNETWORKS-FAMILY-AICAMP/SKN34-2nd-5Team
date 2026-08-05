import { useEffect, useState } from "react";
import { MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

import BusinessAttributeBadges from "../business/BusinessAttributeBadges";
import BusinessPhoto from "../business/BusinessPhoto";
import DatasetRating from "../business/DatasetRating";
import BusinessMapMarker, { MapLegend } from "../map/BusinessMapMarker";
import { loadReviewerRadius } from "../../data";

// Circles are capped at this many km so one distant outlier (a travel
// review) doesn't shrink the entire local cluster to invisibility — real
// v04 data has exactly this case (a Tampa-centered reviewer with four
// New Orleans reviews ~765km out). Points beyond the cap go in the
// out-of-scale inset instead of being silently dropped.
const SCALE_CAP_KM = 40;

const VIEWPORT_PX = 320;
const CENTER_PX = VIEWPORT_PX / 2;
const RENDER_RADIUS_PX = 130;
// The scale bar lives in its own strip below the circle chart, not
// overlapping it — at full render radius the circle's bottom edge sits
// right at VIEWPORT_PX, so sharing that y-coordinate with the scale bar
// made the two read as touching/overlapping.
const SCALE_BAR_AREA_PX = 46;
const SVG_HEIGHT_PX = VIEWPORT_PX + SCALE_BAR_AREA_PX;
const SCALE_BAR_LABEL_Y = VIEWPORT_PX + 20;
const SCALE_BAR_LINE_Y = VIEWPORT_PX + 30;

function toXY(distanceKm, bearingDeg, pxPerKm) {
  const rad = (bearingDeg * Math.PI) / 180;
  return {
    x: CENTER_PX + distanceKm * pxPerKm * Math.sin(rad),
    y: CENTER_PX - distanceKm * pxPerKm * Math.cos(rad),
  };
}

// Marks a clipped ring with 4 outward ticks so it reads as "cut off here",
// not as the true edge of the P90 disk.
function ClipTicks({ radius, color }) {
  return (
    <>
      {[0, 90, 180, 270].map((deg) => {
        const rad = (deg * Math.PI) / 180;
        const x1 = CENTER_PX + radius * Math.sin(rad);
        const y1 = CENTER_PX - radius * Math.cos(rad);
        const x2 = CENTER_PX + (radius + 7) * Math.sin(rad);
        const y2 = CENTER_PX - (radius + 7) * Math.cos(rad);
        return <line key={deg} x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth="2" />;
      })}
    </>
  );
}

const MAP_WIDTH = 520;
const MAP_HEIGHT = 250;
const MAP_BOUNDS = { minLatitude: 22, maxLatitude: 55, minLongitude: -128, maxLongitude: -62 };

function projectMapPoint(latitude, longitude, width = MAP_WIDTH, height = MAP_HEIGHT) {
  return {
    x: ((longitude - MAP_BOUNDS.minLongitude) / (MAP_BOUNDS.maxLongitude - MAP_BOUNDS.minLongitude)) * width,
    y: ((MAP_BOUNDS.maxLatitude - latitude) / (MAP_BOUNDS.maxLatitude - MAP_BOUNDS.minLatitude)) * height,
  };
}

function ActivityRegionMap({ period, mapRegions }) {
  const { primaryRegion, satelliteRegions, additionalRegionCount, primaryZones } = mapRegions;
  const overviewPoints = [primaryRegion, ...satelliteRegions];
  const zoneLatitudes = primaryZones.map((zone) => zone.latitude);
  const zoneLongitudes = primaryZones.map((zone) => zone.longitude);
  const zoneBounds = {
    minLatitude: Math.min(...zoneLatitudes, primaryRegion.latitude - 0.35),
    maxLatitude: Math.max(...zoneLatitudes, primaryRegion.latitude + 0.35),
    minLongitude: Math.min(...zoneLongitudes, primaryRegion.longitude - 0.45),
    maxLongitude: Math.max(...zoneLongitudes, primaryRegion.longitude + 0.45),
  };
  const zoomPoint = (zone) => ({
    x: 16 + ((zone.longitude - zoneBounds.minLongitude) / (zoneBounds.maxLongitude - zoneBounds.minLongitude)) * 118,
    y: 46 + ((zoneBounds.maxLatitude - zone.latitude) / (zoneBounds.maxLatitude - zoneBounds.minLatitude)) * 36,
  });

  return (
    <div className="mt-3 grid gap-3 lg:grid-cols-[minmax(0,1.45fr)_minmax(220px,0.8fr)]">
      <div className="rounded-md border border-[#DDE4DF] bg-[#FCFDFC] p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-xs font-medium text-[#17211D]">{period.activityYear}년 리뷰 활동 권역</p>
          <span className="text-[10px] text-[#626D67]">도시·권역 단위 표시</span>
        </div>
        <svg viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`} className="h-auto w-full" role="img" aria-label={`${period.activityYear}년 도시 권역 단위 리뷰 활동 분포 지도`}>
          <rect width={MAP_WIDTH} height={MAP_HEIGHT} rx="8" fill="#F5F8F5" />
          {[80, 170, 260, 350, 440].map((x) => <line key={`v-${x}`} x1={x} y1="12" x2={x} y2={MAP_HEIGHT - 12} stroke="#E0E8E2" strokeWidth="1" />)}
          {[62, 125, 188].map((y) => <line key={`h-${y}`} x1="12" y1={y} x2={MAP_WIDTH - 12} y2={y} stroke="#E0E8E2" strokeWidth="1" />)}
          <text x="18" y="28" fill="#7A8780" fontSize="10">North America · generalized activity regions</text>
          {satelliteRegions.map((region) => {
            const from = projectMapPoint(primaryRegion.latitude, primaryRegion.longitude);
            const to = projectMapPoint(region.latitude, region.longitude);
            return <line key={`line-${region.city}`} x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#D89A8D" strokeDasharray="4 4" strokeWidth="1.5" />;
          })}
          {overviewPoints.map((region, index) => {
            const { x, y } = projectMapPoint(region.latitude, region.longitude);
            const isPrimary = index === 0;
            return (
              <g key={`${region.city}-${index}`}>
                <circle cx={x} cy={y} r={isPrimary ? 9 : 6} fill={isPrimary ? "#137A5A" : "#E86A54"} fillOpacity={isPrimary ? "0.95" : "0.88"} />
                <circle cx={x} cy={y} r={isPrimary ? 14 : 10} fill="none" stroke={isPrimary ? "#137A5A" : "#E86A54"} strokeOpacity="0.24" />
                <text x={x + 12} y={y - 9} fill="#34413B" fontSize="10">{region.city}</text>
                <title>{`${region.city}: 리뷰 ${region.reviewCount}건, 음식점 ${region.venueCount}곳`}</title>
              </g>
            );
          })}
          <g transform="translate(352 135)">
            <rect width="150" height="98" rx="6" fill="#FFFFFF" stroke="#DDE4DF" />
            <text x="10" y="17" fill="#17211D" fontSize="10" fontWeight="600">주 활동 권역 확대</text>
            <text x="10" y="31" fill="#626D67" fontSize="9">{primaryRegion.city} · 권역 단위</text>
            <rect x="9" y="39" width="132" height="50" rx="4" fill="#F5F8F5" />
            {primaryZones.map((zone, index) => {
              const { x, y } = zoomPoint(zone);
              return <circle key={`zone-${index}`} cx={x} cy={y} r={Math.min(7, 3 + Math.sqrt(zone.reviewCount))} fill="#137A5A" fillOpacity="0.8"><title>{`권역 내 활동 묶음: 리뷰 ${zone.reviewCount}건, 음식점 ${zone.venueCount}곳`}</title></circle>;
            })}
          </g>
        </svg>
      </div>

      <div className="space-y-2 rounded-md border border-[#DDE4DF] bg-white p-3">
        <div>
          <p className="text-xs font-medium text-[#17211D]">주 활동 권역</p>
          <p className="mt-1 text-sm font-semibold text-[#137A5A]">{primaryRegion.city}</p>
          <p className="mt-0.5 text-[11px] text-[#626D67]">리뷰 {primaryRegion.reviewCount}건 · 음식점 {primaryRegion.venueCount}곳</p>
        </div>
        {satelliteRegions.length > 0 ? (
          <div className="border-t border-[#EEF1EE] pt-2">
            <p className="text-xs font-medium text-[#17211D]">원거리 활동 권역 · {satelliteRegions.length + additionalRegionCount}곳</p>
            <ul className="mt-1.5 space-y-1 text-[11px] text-[#626D67]">
              {satelliteRegions.map((region) => <li key={region.city}>{region.city} · 약 {region.distanceFromPrimaryKm.toLocaleString()}km · 리뷰 {region.reviewCount}건</li>)}
              {additionalRegionCount > 0 && <li>그 외 권역 {additionalRegionCount}곳</li>}
            </ul>
          </div>
        ) : (
          <p className="border-t border-[#EEF1EE] pt-2 text-[11px] text-[#626D67]">별도 원거리 활동 권역이 확인되지 않았습니다.</p>
        )}
        <p className="border-t border-[#EEF1EE] pt-2 text-[10px] leading-4 text-[#626D67]">개별 음식점·정확한 좌표는 표시하지 않습니다. 이 분포는 실제 거주지나 생활 이동을 뜻하지 않습니다.</p>
      </div>
    </div>
  );
}

function MapViewport({ businesses, focus }) {
  const map = useMap();
  const pointKey = businesses.map((business) => `${business.latitude}:${business.longitude}`).join("|");

  useEffect(() => {
    if (!businesses.length) return;
    if (focus === "primary") {
      map.setView([businesses[0].latitude, businesses[0].longitude], 12);
      return;
    }
    map.fitBounds(businesses.map((business) => [business.latitude, business.longitude]), {
      padding: [36, 36],
      maxZoom: 12,
    });
  }, [map, focus, pointKey, businesses]);

  return null;
}

function MapAutoResize() {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();
    let frameId = window.requestAnimationFrame(() => map.invalidateSize({ pan: false }));
    const observer = new ResizeObserver(() => {
      window.cancelAnimationFrame(frameId);
      frameId = window.requestAnimationFrame(() => map.invalidateSize({ pan: false }));
    });
    observer.observe(container);
    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frameId);
    };
  }, [map]);

  return null;
}

function ActualActivityMap({ period, mapRegions }) {
  const [focus, setFocus] = useState("all");
  const businesses = period.businesses?.filter((business) => Number.isFinite(business.latitude) && Number.isFinite(business.longitude)) ?? [];
  const [selectedId, setSelectedId] = useState(null);

  if (!businesses.length) return <ActivityRegionMap period={period} mapRegions={mapRegions} />;

  const primaryCity = mapRegions?.primaryRegion?.city;
  const primaryBusinesses = primaryCity ? businesses.filter((business) => business.city === primaryCity) : businesses;
  const displayBusinesses = focus === "primary" && primaryBusinesses.length ? primaryBusinesses : businesses;
  const selectedBusiness = displayBusinesses.find((business) => business.businessId === selectedId)
    ?? [...displayBusinesses].sort((a, b) => b.reviewCount - a.reviewCount
      || Number(Boolean(b.photos?.length)) - Number(Boolean(a.photos?.length))
      || a.distanceKm - b.distanceKm
      || a.name.localeCompare(b.name))[0];
  const yelpSearchUrl = selectedBusiness
    ? `https://www.yelp.com/search?find_desc=${encodeURIComponent(selectedBusiness.name)}&find_loc=${encodeURIComponent(`${selectedBusiness.city}, ${selectedBusiness.state}`)}`
    : null;
  const activityVariant = period.activityYear === 2017 ? "activityPrevious" : "activityCurrent";

  return (
    <div className="mt-3 flex min-h-0 flex-1 flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-[#626D67]">핀을 선택하면 오른쪽에서 음식점 사진·평점·리뷰 수·주소를 확인할 수 있습니다.</p>
        <div className="inline-flex rounded border border-[#DDE4DF] bg-[#F7F8F5] p-0.5 text-[11px]">
          <button type="button" onClick={() => setFocus("all")} className={`rounded px-2.5 py-1 ${focus === "all" ? "bg-white font-medium text-[#17211D] shadow-sm" : "text-[#626D67]"}`}>전체 활동</button>
          <button type="button" onClick={() => setFocus("primary")} className={`rounded px-2.5 py-1 ${focus === "primary" ? "bg-white font-medium text-[#17211D] shadow-sm" : "text-[#626D67]"}`}>주 활동 권역 확대</button>
        </div>
      </div>
      <div className="relative min-w-0">
        <div className="relative min-h-[520px] min-w-0 flex-1 overflow-hidden rounded-lg border border-[#DDE4DF]" role="region" aria-label={`${period.activityYear}년 음식점 리뷰 활동 지도`}>
          <div className="absolute inset-0">
            <MapContainer center={[businesses[0].latitude, businesses[0].longitude]} zoom={10} scrollWheelZoom className="h-full w-full">
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <MapAutoResize />
              <MapViewport businesses={displayBusinesses} focus={focus} />
              {displayBusinesses.map((business) => (
                <BusinessMapMarker
                  key={`${business.businessId}-${business.latitude}-${business.longitude}`}
                  position={[business.latitude, business.longitude]}
                  variant={activityVariant}
                  selected={business.businessId === selectedBusiness?.businessId}
                  eventHandlers={{ click: () => setSelectedId(business.businessId) }}
                >
                  <Popup>
                    <div className="min-w-[190px] space-y-1.5 text-sm">
                      <p className="font-semibold text-[#17211D]">{business.name}</p>
                      <p className="text-xs text-[#626D67]">{business.city}, {business.state}</p>
                      <p className="rounded bg-[#F1F4F1] px-2 py-1 text-xs font-bold text-[#4F5D56]">{period.activityYear}년 리뷰 {business.reviewCount}건 · 상세 정보는 오른쪽에서 확인</p>
                    </div>
                  </Popup>
                </BusinessMapMarker>
              ))}
            </MapContainer>
          </div>
          <MapLegend className="absolute bottom-6 left-3 z-[500]" items={[{ variant: activityVariant, label: `${period.activityYear}년 리뷰 활동 지점` }]} />
        </div>

        {selectedBusiness && (
          <aside className="mt-3 min-w-0 overflow-hidden rounded-xl border border-[#C9D5CE] bg-white shadow-[0_12px_30px_rgba(23,33,29,0.16)] xl:absolute xl:bottom-3 xl:right-3 xl:top-3 xl:z-[600] xl:mt-0 xl:flex xl:w-[32%] xl:min-w-[320px] xl:max-w-[360px] xl:flex-col" aria-label="선택 음식점 상세 정보">
            <BusinessPhoto photos={selectedBusiness.photos} alt={`${selectedBusiness.name} 데이터셋 사진`} className="h-[36%] min-h-[170px] max-h-[210px] w-full shrink-0" fit="contain" />
            <div className="space-y-3 p-4 xl:min-h-0 xl:flex-1 xl:overflow-y-auto">
              <div>
                <p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">SELECTED ACTIVITY</p>
                <h3 className="mt-0.5 text-base font-black text-[#17211D]">{selectedBusiness.name}</h3>
                <p className="mt-1 text-xs text-[#626D67]">{selectedBusiness.city}, {selectedBusiness.state}</p>
              </div>
              {selectedBusiness.categories?.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {selectedBusiness.categories.slice(0, 2).map((category) => <span key={category} className="rounded-full bg-[#F1F4F1] px-2 py-1 text-[10px] font-bold text-[#4F5D56]">{category}</span>)}
                </div>
              )}
              {Number.isFinite(selectedBusiness.stars) && Number.isFinite(selectedBusiness.datasetReviewCount) && (
                <DatasetRating stars={selectedBusiness.stars} reviewCount={selectedBusiness.datasetReviewCount} compact />
              )}
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg bg-[#F0F7F3] p-3"><p className="text-[10px] text-[#626D67]">리뷰어 활동</p><p className="mt-1 text-base font-black text-[#075C45]">{period.activityYear}년 {selectedBusiness.reviewCount}건</p></div>
                <div className="rounded-lg bg-[#F7F8F5] p-3"><p className="text-[10px] text-[#626D67]">기간 중심과 거리</p><p className="mt-1 text-base font-black text-[#17211D]">{selectedBusiness.distanceKm.toLocaleString()}km</p></div>
              </div>
              <details className="rounded-lg border border-[#E3E8E4] bg-[#F8FAF8] px-2.5 py-2">
                <summary className="cursor-pointer text-[10px] font-bold text-[#4F5D56]">편의·주소 상세</summary>
                <div className="mt-2"><BusinessAttributeBadges attributes={selectedBusiness.displayAttributes} compact showAddress /></div>
              </details>
              <a
                href={yelpSearchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex min-h-10 w-full items-center justify-center rounded-lg border border-[#075C45] bg-white px-3 text-xs font-black text-[#075C45] transition hover:bg-[#F0F7F3]"
              >
                Yelp에서 음식점 검색 ↗
              </a>
              <p className="text-[10px] leading-4 text-[#718078]">사진·평점·리뷰 수는 Yelp Open Dataset 수집 시점 기준입니다.</p>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

function RecommendationMap({ restaurants, radiusContext }) {
  return (
    <div className="mt-3 flex min-h-0 flex-1 flex-col gap-2">
      <div className="rounded-lg border border-[#F1B7AB] bg-[#FFF5F2] px-3 py-2 text-xs leading-5 text-[#9F4A38]">추천 후보 위치는 관심 카테고리 기반 사업장 위치이며 리뷰 활동 반경·거주지·생활권과 별도 정보입니다.</div>
      {radiusContext && <div className="rounded-lg border border-[#B7D8C8] bg-[#F0F7F3] px-3 py-2 text-xs leading-5 text-[#4F5D56]"><strong className="text-[#075C45]">주 활동 권역 검색</strong> · 전체 활동 P90 {radiusContext.observedP90RadiusKm.toLocaleString()}km → 50km 기준 {radiusContext.activityClusterCount}개 권역 중 주 권역 {radiusContext.primaryClusterBusinessCount}곳 → 주 권역 P90 {radiusContext.primaryClusterP90RadiusKm.toLocaleString()}km · 실제 검색 {radiusContext.appliedSearchRadiusKm.toLocaleString()}km{radiusContext.multiRegionActivity && ` · 원거리 ${radiusContext.remoteRegionCount}개 권역·${radiusContext.travelOutlierCount}곳 분리`}{radiusContext.radiusCapApplied && " · 50km 상한 적용"}</div>}
      <div className="relative min-h-[520px] flex-1 overflow-hidden rounded-lg border border-[#DDE4DF]" role="region" aria-label="개인 추천 음식점 지도">
        <div className="absolute inset-0">
          <MapContainer center={[restaurants[0].latitude, restaurants[0].longitude]} zoom={11} scrollWheelZoom className="h-full w-full">
            <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <MapAutoResize />
            <MapViewport businesses={restaurants} focus="all" />
            {restaurants.map((restaurant) => (
              <BusinessMapMarker key={restaurant.businessId} position={[restaurant.latitude, restaurant.longitude]} variant="recommendation">
                <Popup><div className="min-w-[210px] space-y-2 text-sm"><BusinessPhoto photos={restaurant.photos} alt={`${restaurant.name} 데이터셋 사진`} className="h-24 w-full" compact /><div><p className="font-semibold text-[#17211D]">{restaurant.name}</p><p className="text-xs text-[#626D67]">{restaurant.city}, {restaurant.state} · {restaurant.primaryCategory}</p></div><DatasetRating stars={restaurant.stars} reviewCount={restaurant.reviewCount} compact /><span className={`inline-flex rounded-full px-2 py-1 text-[9px] font-black ${restaurant.distanceBand === "core" ? "bg-[#E7F3ED] text-[#075C45]" : "bg-[#FFF1ED] text-[#9F4A38]"}`}>{restaurant.distanceKm.toLocaleString()}km · {restaurant.distanceBand === "core" ? "핵심 활동권" : "확장 후보"}</span><BusinessAttributeBadges attributes={restaurant.displayAttributes} compact showAddress /></div></Popup>
              </BusinessMapMarker>
            ))}
          </MapContainer>
        </div>
        <MapLegend className="absolute bottom-6 left-3 z-[500]" items={[{ variant: "recommendation", label: "맞춤 추천 후보" }]} />
      </div>
    </div>
  );
}

function ReviewActivityRadius({ userId, recommendationData }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [visualMode, setVisualMode] = useState("activity");

  useEffect(() => {
    let active = true;
    loadReviewerRadius(userId)
      .then((json) => {
        if (active) setData(json);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [userId]);

  if (error) {
    return (
      <div className="rounded-lg border border-[#DDE4DF] bg-white p-4 text-xs text-[#8A3B2E]">
        {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-lg border border-[#DDE4DF] bg-white p-4 text-xs text-[#626D67]">
        불러오는 중…
      </div>
    );
  }

  if (!data.available || (!data.comparison?.available && !data.selection?.available)) {
    return (
      <div className="rounded-lg border border-[#DDE4DF] bg-white p-4">
        <p className="text-sm font-medium text-[#17211D]">리뷰 활동 반경</p>
        <p className="mt-2 text-xs text-[#626D67]">
          이 리뷰어는 활동 음식점이 2곳 미만이라 반경을 계산할 수 없습니다.
        </p>
      </div>
    );
  }

  const { comparison, selection, change } = data;
  const hasComparison = Boolean(comparison?.available);
  const hasSelection = Boolean(selection?.available);
  const bothAvailable = hasComparison && hasSelection;
  // Single-period view uses whichever period actually has data — in
  // practice this is always "selection" (comparison year is the one that
  // can be missing), but this stays correct either way.
  const soloPeriod = hasSelection ? selection : comparison;
  const missingPeriodYear = hasSelection ? comparison?.activityYear : selection?.activityYear;

  const scaleKm = Math.min(
    SCALE_CAP_KM,
    Math.max(comparison?.p90RadiusKm ?? 0, selection?.p90RadiusKm ?? 0, 5),
  );
  const pxPerKm = RENDER_RADIUS_PX / scaleKm;
  const scaleBarKm = Math.min(10, scaleKm);

  const withScale = (period) => {
    if (!period?.available) return { inScale: [], outOfScale: [] };
    const inScale = [];
    const outOfScale = [];
    for (const business of period.businesses) {
      (business.distanceKm <= scaleKm ? inScale : outOfScale).push(business);
    }
    return { inScale, outOfScale };
  };

  const comparisonPoints = withScale(comparison);
  const selectionPoints = withScale(selection);
  const soloPoints = hasSelection ? selectionPoints : comparisonPoints;
  const outOfScale = [
    ...comparisonPoints.outOfScale.map((business) => ({
      ...business,
      activityYear: comparison.activityYear,
    })),
    ...selectionPoints.outOfScale.map((business) => ({
      ...business,
      activityYear: selection.activityYear,
    })),
  ];
  const farthestInScaleKm = soloPoints.inScale.length
    ? Math.max(...soloPoints.inScale.map((business) => business.distanceKm))
    : null;
  const mapPeriod = hasSelection ? selection : comparison;
  const mapRegions = mapPeriod?.mapRegions;
  const hasMapBusinesses = Boolean(mapPeriod?.businesses?.some(
    (business) => Number.isFinite(business.latitude) && Number.isFinite(business.longitude),
  ));
  const recommendationRestaurants = (recommendationData?.recommendations ?? []).filter(
    (restaurant) => Number.isFinite(restaurant.latitude) && Number.isFinite(restaurant.longitude),
  );

  // Radii that exceed the render cap are drawn AT the cap, which — without
  // a marker — reads as if the true P90 equals the cap. clipped* flags
  // whether the on-screen ring understates the labeled km figure.
  const comparisonClipped = comparison?.available && comparison.p90RadiusKm > scaleKm;
  const selectionClipped = selection?.available && selection.p90RadiusKm > scaleKm;
  const anyClipped = comparisonClipped || selectionClipped;
  const comparisonRadiusPx = comparison?.available
    ? Math.min(comparison.p90RadiusKm, scaleKm) * pxPerKm
    : null;
  const selectionRadiusPx = selection?.available
    ? Math.min(selection.p90RadiusKm, scaleKm) * pxPerKm
    : null;

  const comparisonCity = comparison?.mapRegions?.primaryRegion?.city;
  const selectionCity = selection?.mapRegions?.primaryRegion?.city;
  const cityChanged = Boolean(
    bothAvailable && comparisonCity && selectionCity && comparisonCity !== selectionCity,
  );

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-[#DDE4DF] bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E2E7E3] px-4 py-2.5">
        <div><p className="text-[9px] font-black tracking-[0.12em] text-[#137A5A]">REVIEW ACTIVITY MAP</p><p className="mt-0.5 text-sm font-black text-[#17211D]">
          {bothAvailable ? "리뷰 활동 반경" : `${soloPeriod.activityYear}년 리뷰 활동 분포`}
        </p></div>
        {!bothAvailable && missingPeriodYear && (
          <span className="whitespace-nowrap rounded bg-[#F1F4F1] px-1.5 py-0.5 text-[10px] text-[#626D67]">
            {missingPeriodYear}년 비교 기록 없음
          </span>
        )}
      </div>

      {bothAvailable && (
        <div className="mx-4 mt-3 flex flex-wrap gap-x-5 gap-y-1 rounded-lg bg-[#F7F9F7] px-3 py-2 text-[11px]">
          <p className="flex items-center gap-1.5 text-[#A66A18]">
            <span className="inline-block h-2 w-2 rounded-full border-2 border-[#A66A18]" />
            {comparison.activityYear}년 비교 기간 · P90 반경 {comparison.p90RadiusKm}km
            {comparisonClipped && <span className="text-[#626D67]"> · 차트 범위 초과</span>}
          </p>
          <p className="flex items-center gap-1.5 text-[#137A5A]">
            <span className="inline-block h-2 w-2 rounded-full bg-[#137A5A]" />
            {selection.activityYear}년 선정 기간 · P90 반경 {selection.p90RadiusKm}km
            {selectionClipped && <span className="text-[#626D67]"> · 차트 범위 초과</span>}
          </p>
          {change?.radiusChangeKm != null && (
            <p className="text-[#626D67]">
              변화 {change.radiusChangeKm > 0 ? "+" : ""}
              {change.radiusChangeKm}km
            </p>
          )}
        </div>
      )}

      {(hasMapBusinesses || recommendationRestaurants.length > 0) && (
        <div className="mx-4 mt-3 inline-flex rounded-lg border border-[#DDE4DF] bg-[#F7F8F5] p-1 text-[11px]">
          <button type="button" onClick={() => setVisualMode("activity")} className={`rounded-md px-3 py-1.5 ${visualMode === "activity" ? "bg-[#075C45] font-bold text-white shadow-sm" : "text-[#626D67]"}`}>활동 근거</button>
          {recommendationRestaurants.length > 0 && <button type="button" onClick={() => setVisualMode("recommendations")} className={`rounded-md px-3 py-1.5 ${visualMode === "recommendations" ? "bg-[#075C45] font-bold text-white shadow-sm" : "text-[#626D67]"}`}>추천 후보</button>}
          <button type="button" onClick={() => setVisualMode("radius")} className={`rounded-md px-3 py-1.5 ${visualMode === "radius" ? "bg-[#075C45] font-bold text-white shadow-sm" : "text-[#626D67]"}`}>반경 비교</button>
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col px-4 pb-4">
      {visualMode === "recommendations" && recommendationRestaurants.length > 0 ? (
        <RecommendationMap restaurants={recommendationRestaurants} radiusContext={recommendationData?.radiusContext} />
      ) : visualMode === "activity" && hasMapBusinesses ? (
        <ActualActivityMap period={mapPeriod} mapRegions={mapRegions} />
      ) : (
      <>
      {cityChanged && (
        <div className="mt-3 rounded-lg border border-[#B7D8C8] bg-[#F0F7F3] p-3">
          <p className="text-[9px] font-black tracking-[0.1em] text-[#137A5A]">왜 추천 지역이 바뀌었나</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[13px] font-bold text-[#17211D]">
            <span className="font-normal text-[#626D67]">{comparison.activityYear}년 주 활동 도시</span>
            <span>{comparisonCity}</span>
            <span className="text-[#075C45]">→</span>
            <span className="font-normal text-[#626D67]">{selection.activityYear}년</span>
            <span className="text-[#075C45]">{selectionCity}</span>
          </div>
          <p className="mt-1.5 text-[11px] leading-5 text-[#4F5D56]">
            활동 중심이 {change?.centerShiftKm ?? "—"}km 이동해서, <span className="font-bold">추천 후보</span> 탭의 음식점 추천도 이제 {selectionCity} 기준으로 자동 계산됩니다.
          </p>
          {recommendationRestaurants.length > 0 && (
            <button
              type="button"
              onClick={() => setVisualMode("recommendations")}
              className="mt-2 min-h-9 rounded-lg border border-[#075C45] bg-white px-3 text-[11px] font-bold text-[#075C45] hover:bg-[#F0F7F3]"
            >
              추천 후보 탭에서 확인 →
            </button>
          )}
        </div>
      )}
      <div className="mt-3 flex flex-col gap-3 sm:flex-row">
        <svg
          viewBox={`0 0 ${VIEWPORT_PX} ${SVG_HEIGHT_PX}`}
          className="h-auto w-full max-w-[320px] shrink-0 self-center"
          role="img"
          aria-label="리뷰 활동 반경을 중심 기준 상대 거리로 표시한 산점도. 절대 좌표는 표시하지 않습니다."
        >
          <line x1={CENTER_PX - 6} y1={CENTER_PX} x2={CENTER_PX + 6} y2={CENTER_PX} stroke="#B3BBB6" />
          <line x1={CENTER_PX} y1={CENTER_PX - 6} x2={CENTER_PX} y2={CENTER_PX + 6} stroke="#B3BBB6" />

          {anyClipped && (
            <circle
              cx={CENTER_PX}
              cy={CENTER_PX}
              r={RENDER_RADIUS_PX}
              fill="none"
              stroke="#B3BBB6"
              strokeWidth="1"
              strokeDasharray="2 3"
            />
          )}

          {comparisonRadiusPx !== null && !comparisonClipped && (
            <circle
              cx={CENTER_PX}
              cy={CENTER_PX}
              r={comparisonRadiusPx}
              fill="none"
              stroke="#A66A18"
              strokeWidth="1.5"
              strokeDasharray="5 4"
            />
          )}
          {comparisonRadiusPx !== null && comparisonClipped && (
            <>
              <circle
                cx={CENTER_PX}
                cy={CENTER_PX}
                r={comparisonRadiusPx}
                fill="none"
                stroke="#A66A18"
                strokeWidth="1.5"
                strokeDasharray="2 4"
              />
              <ClipTicks radius={comparisonRadiusPx} color="#A66A18" />
            </>
          )}

          {selectionRadiusPx !== null && !selectionClipped && (
            <circle
              cx={CENTER_PX}
              cy={CENTER_PX}
              r={selectionRadiusPx}
              fill="#E3F1EA"
              fillOpacity="0.8"
              stroke="#137A5A"
              strokeWidth="1.5"
            />
          )}
          {selectionRadiusPx !== null && selectionClipped && (
            <>
              <circle
                cx={CENTER_PX}
                cy={CENTER_PX}
                r={selectionRadiusPx}
                fill="none"
                stroke="#137A5A"
                strokeWidth="1.5"
                strokeDasharray="2 4"
              />
              <ClipTicks radius={selectionRadiusPx} color="#137A5A" />
            </>
          )}

          {comparisonPoints.inScale.map((business, index) => {
            const { x, y } = toXY(business.distanceKm, business.bearingDeg, pxPerKm);
            return (
              <circle
                key={`c-${index}`}
                cx={x}
                cy={y}
                r="3.5"
                fill="#fff"
                stroke="#A66A18"
                strokeWidth="1.5"
              >
                <title>{`${comparison.activityYear}년 · ${business.name} · ${business.city} · ${business.distanceKm}km`}</title>
              </circle>
            );
          })}
          {selectionPoints.inScale.map((business, index) => {
            const { x, y } = toXY(business.distanceKm, business.bearingDeg, pxPerKm);
            return (
              <circle key={`s-${index}`} cx={x} cy={y} r="3.5" fill="#137A5A">
                <title>{`${selection.activityYear}년 · ${business.name} · ${business.city} · ${business.distanceKm}km`}</title>
              </circle>
            );
          })}

          {!bothAvailable && (
            <text x={CENTER_PX} y={VIEWPORT_PX - 8} textAnchor="middle" fill="#137A5A" fontSize="11">
              {soloPeriod.activityYear}년 반경 {soloPeriod.p90RadiusKm}km
            </text>
          )}

          <line x1={20} y1={VIEWPORT_PX + 4} x2={VIEWPORT_PX - 20} y2={VIEWPORT_PX + 4} stroke="#EEF1EE" />
          <line x1={20} y1={SCALE_BAR_LINE_Y} x2={20 + scaleBarKm * pxPerKm} y2={SCALE_BAR_LINE_Y} stroke="#626D67" />
          <text x={20} y={SCALE_BAR_LABEL_Y} fill="#626D67" fontSize="10">
            {scaleBarKm}km · 상대 거리{anyClipped ? ` · 표시 범위 최대 ${SCALE_CAP_KM}km` : ""}
          </text>
        </svg>

        <div className="min-w-0 flex-1 space-y-2.5">
          {!bothAvailable && (
            <div className="rounded border border-[#DDE4DF] p-2.5">
              <p className="text-xs font-medium text-[#17211D]">{soloPeriod.activityYear}년 활동 요약</p>
              <dl className="mt-1.5 space-y-1 text-[11px] text-[#626D67]">
                <div className="flex justify-between">
                  <dt>P90 활동 반경</dt>
                  <dd className="text-[#17211D]">{soloPeriod.p90RadiusKm}km</dd>
                </div>
                <div className="flex justify-between">
                  <dt>표시된 음식점</dt>
                  <dd className="text-[#17211D]">{soloPoints.inScale.length}곳</dd>
                </div>
                <div className="flex justify-between">
                  <dt>표시 축척 밖 원거리 활동</dt>
                  <dd className="text-[#17211D]">{soloPoints.outOfScale.length}곳</dd>
                </div>
                {farthestInScaleKm !== null && (
                  <div className="flex justify-between">
                    <dt>가장 먼 표시 활동</dt>
                    <dd className="text-[#17211D]">약 {Math.round(farthestInScaleKm)}km</dd>
                  </div>
                )}
              </dl>
            </div>
          )}

          {outOfScale.length > 0 ? (
            <div className="rounded border border-dashed border-[#DDE4DF] p-2.5">
              <p className="text-xs font-medium text-[#17211D]">
                표시 축척 밖 원거리 활동 · {outOfScale.length}곳
              </p>
              <ul className="mt-1.5 space-y-1">
                {outOfScale.map((business, index) => (
                  <li key={index} className="text-[11px] text-[#626D67]">
                    {business.activityYear}년 · {business.city} · 약 {Math.round(business.distanceKm)}km
                  </li>
                ))}
              </ul>
              <p className="mt-1.5 text-[11px] text-[#626D67]">
                축척 밖 원거리 활동입니다. P90 정의상 일부 활동은 원 밖에 위치할 수 있으므로 활동 맥락을 확인하세요.
              </p>
            </div>
          ) : (
            <p className="text-xs text-[#626D67]">표시 축척 밖 원거리 활동 없음</p>
          )}

          {bothAvailable && change && (
            <div className="rounded bg-[#F7F8F5] p-2.5">
              <p className="text-[11px] text-[#626D67]">
                기간별 리뷰 분포 중심 간 거리 {change.centerShiftKm ?? "—"}km
              </p>
            </div>
          )}
        </div>
      </div>
      </>
      )}

      {visualMode === "recommendations" ? (
        <p className="mt-3 text-[11px] leading-5 text-[#626D67]">
          추천 음식점은 긍정 리뷰 카테고리와 미방문 조건을 기준으로 선정한 운영 후보입니다.
          음식점 공개 위치를 표시하며 리뷰어의 거주지나 실제 생활권을 의미하지 않습니다.
        </p>
      ) : visualMode === "activity" && hasMapBusinesses ? (
        <p className="mt-3 text-[11px] leading-5 text-[#626D67]">
          음식점 공개 위치를 기반으로 한 리뷰 활동 지도입니다. 리뷰어의 거주지나 실제 이동 경로를 의미하지 않습니다.
        </p>
      ) : (
        <p className="mt-3 text-[11px] leading-5 text-[#626D67]">
          각 기간의 중심점을 원점으로 다시 배치한 상대 분포입니다.<br />
          리뷰 분포의 통계적 중심 차이이며 실제 거주지나 생활 이동을 의미하지 않습니다.<br />
          반경 축소는 v04 검증에서 위험 예측 피처로 채택되지 않았습니다.
        </p>
      )}
      </div>
    </div>
  );
}

export default ReviewActivityRadius;
