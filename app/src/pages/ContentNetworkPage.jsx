import { useEffect, useMemo, useState } from "react";
import { MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import { Link, useSearchParams } from "react-router";
import "leaflet/dist/leaflet.css";

import DataModeBadge from "../components/DataModeBadge";
import BusinessAttributeBadges from "../components/business/BusinessAttributeBadges";
import BusinessPhoto from "../components/business/BusinessPhoto";
import DatasetRating from "../components/business/DatasetRating";
import ErrorState from "../components/common/ErrorState";
import Skeleton from "../components/common/Skeleton";
import BusinessMapMarker, { MapLegend } from "../components/map/BusinessMapMarker";
import WorkflowContextBar from "../components/workflow/WorkflowContextBar";
import WorkflowHeader from "../components/workflow/WorkflowHeader";
import { useReviewers, useRiskTypes } from "../context/operations-context";
import { loadRegionalCampaignRestaurants, loadRegionalDerivedContext } from "../data";

function MapFocus({ restaurants, selected }) {
  const map = useMap();
  const focus = selected ?? restaurants[0];
  useEffect(() => {
    if (!focus) return;
    if (selected) map.setView([focus.latitude, focus.longitude], 13);
    else map.fitBounds(restaurants.map((restaurant) => [restaurant.latitude, restaurant.longitude]), { padding: [40, 40], maxZoom: 11 });
  }, [focus, map, restaurants, selected]);
  return null;
}

function ContentNetworkPage() {
  const reviewers = useReviewers();
  const riskTypes = useRiskTypes();
  const [searchParams, setSearchParams] = useSearchParams();
  const [derived, setDerived] = useState(null);
  const [restaurantResult, setRestaurantResult] = useState(null);
  const [error, setError] = useState(null);
  const [selectedRestaurantId, setSelectedRestaurantId] = useState(null);
  const selectedRisk = searchParams.get("riskType") ?? "전체";

  useEffect(() => {
    let active = true;
    loadRegionalDerivedContext()
      .then((data) => { if (active && data.available) setDerived(data); })
      .catch((loadError) => { if (active) setError(loadError.message); });
    return () => { active = false; };
  }, []);

  const topCityByRegion = useMemo(() => {
    const lookup = new Map();
    reviewers.forEach((reviewer) => {
      if (reviewer.region && reviewer.topCity && !lookup.has(reviewer.region)) {
        lookup.set(reviewer.region, reviewer.topCity);
      }
    });
    return lookup;
  }, [reviewers]);
  const regions = useMemo(
    () => [...(derived?.regions ?? [])]
      .map((region) => ({
        ...region,
        topCity: region.topCity ?? topCityByRegion.get(region.region) ?? "대표 활동 도시 확인 불가",
      }))
      .sort((first, second) => (first.reviewSupplyChangeRate ?? 0) - (second.reviewSupplyChangeRate ?? 0)),
    [derived, topCityByRegion],
  );
  const selectedRegion = searchParams.get("region") ?? regions[0]?.region ?? null;
  const regionData = regions.find((region) => region.region === selectedRegion) ?? null;

  const candidates = useMemo(() => reviewers
    .filter((reviewer) => reviewer.region === selectedRegion && reviewer.crmTarget)
    .filter((reviewer) => selectedRisk === "전체" || reviewer.riskType === selectedRisk)
    .sort((first, second) => first.priorityRank - second.priorityRank), [reviewers, selectedRegion, selectedRisk]);
  const sampleIdsKey = candidates.map((candidate) => candidate.sampleId).join(",");
  const requestKey = `${selectedRegion}:${sampleIdsKey}`;

  const restaurants = useMemo(() => {
    if (restaurantResult?.requestKey !== requestKey) return [];
    const uniqueByBusinessId = new Map();
    (restaurantResult.restaurants ?? []).forEach((restaurant) => {
      if (!uniqueByBusinessId.has(restaurant.businessId)) {
        uniqueByBusinessId.set(restaurant.businessId, restaurant);
      }
    });
    return [...uniqueByBusinessId.values()].filter(
      (restaurant) => Number.isFinite(restaurant.latitude) && Number.isFinite(restaurant.longitude),
    );
  }, [requestKey, restaurantResult]);

  useEffect(() => {
    let active = true;
    if (!selectedRegion || !sampleIdsKey) return undefined;
    loadRegionalCampaignRestaurants(selectedRegion, sampleIdsKey.split(","))
      .then((data) => { if (active) setRestaurantResult({ ...data, requestKey: `${selectedRegion}:${sampleIdsKey}` }); })
      .catch((loadError) => { if (active) setRestaurantResult({ available: false, restaurants: [], requestKey: `${selectedRegion}:${sampleIdsKey}`, error: loadError.message }); });
    return () => { active = false; };
  }, [sampleIdsKey, selectedRegion]);

  function updateParams(updates) {
    const next = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => value === "전체" || !value ? next.delete(key) : next.set(key, value));
    setSearchParams(next, { replace: true });
    setSelectedRestaurantId(null);
  }

  if (error) return <ErrorState message={error} />;
  if (!derived) return <Skeleton rows={5} columns={4} />;

  const selectedRestaurant = restaurants.find((restaurant) => restaurant.businessId === selectedRestaurantId) ?? restaurants[0];

  return (
    <section className="pb-5">
      <WorkflowHeader
        eyebrow="CONTENT NETWORK"
        title="콘텐츠 네트워크"
        description="권역 CRM 후보에게 이미 산출된 실제 음식점 추천을 모아 캠페인에 활용할 콘텐츠 후보를 탐색합니다."
        aside={<DataModeBadge />}
      />

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <MetricCard label="선택 권역" value={selectedRegion ?? "—"} note={regionData?.topCity ?? "대표 활동 도시"} />
        <MetricCard label="CRM 후보" value={`${candidates.length.toLocaleString()}명`} note={selectedRisk === "전체" ? "전체 위험 유형" : selectedRisk} />
        <MetricCard label="실제 음식점 후보" value={`${restaurants.length.toLocaleString()}곳`} note="추천 결과 중 좌표 확인 가능" tone="green" />
      </div>

      <div className="mt-5 rounded-2xl border border-[#DDE4DF] bg-white p-4">
        <div className="grid gap-4 lg:grid-cols-[minmax(220px,0.45fr)_minmax(0,1fr)]">
          <label className="text-xs font-black text-[#4F5D56]">권역<select value={selectedRegion ?? ""} onChange={(event) => updateParams({ region: event.target.value })} className="mt-2 min-h-11 w-full rounded-xl border border-[#DDE4DF] bg-white px-3 text-sm font-bold text-[#17211D] outline-none focus:border-[#075C45]">{regions.map((region) => <option key={region.region} value={region.region}>{region.region} · {region.topCity} · {region.reviewSupplyChangeRate >= 0 ? "+" : ""}{(region.reviewSupplyChangeRate * 100).toFixed(1)}%</option>)}</select></label>
          <div><p className="text-xs font-black text-[#4F5D56]">위험 유형</p><div className="mt-2 flex flex-wrap gap-2">{["전체", ...riskTypes].map((risk) => <button key={risk} type="button" onClick={() => updateParams({ riskType: risk })} className={`min-h-10 rounded-full border px-4 text-xs font-black ${selectedRisk === risk ? "border-[#075C45] bg-[#075C45] text-white" : "border-[#DDE4DF] text-[#626D67]"}`}>{risk}</button>)}</div></div>
        </div>
      </div>

      {regionData && <div className="mt-4"><WorkflowContextBar label="SELECTED CONTENT REGION" title={`${regionData.region} · ${regionData.topCity}`} metrics={[{ label: "리뷰 공급", value: regionData.reviewSupplyChangeRate === null || regionData.reviewSupplyChangeRate === undefined ? "비교 불가" : `${regionData.reviewSupplyChangeRate >= 0 ? "+" : ""}${(regionData.reviewSupplyChangeRate * 100).toFixed(1)}%` }, { label: "활동 리뷰어", value: `${(regionData.activeReviewers ?? 0).toLocaleString()}명` }, { label: "신규 유입", value: `${(regionData.newPowerReviewers ?? 0).toLocaleString()}명` }]} action={<Link to={`/playbook?mode=region&region=${encodeURIComponent(selectedRegion)}&riskType=${encodeURIComponent(selectedRisk)}`} className="flex min-h-10 items-center rounded-lg bg-[#075C45] px-4 text-xs font-black text-white">캠페인에서 사용</Link>} /></div>}

      <div className="mt-4 grid items-start gap-5 xl:grid-cols-[minmax(0,1.35fr)_430px]">
        <section className="rounded-2xl border border-[#DDE4DF] bg-white p-5">
          <div className="flex items-end justify-between gap-3"><div><p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">RESTAURANT MAP</p><h2 className="mt-1 text-lg font-black">실제 음식점 후보 지도</h2></div><span className="text-xs font-black text-[#075C45]">{restaurants.length}곳</span></div>
          {restaurants.length > 0 ? (
            <div className="relative mt-4 overflow-hidden rounded-xl">
              <MapContainer center={[restaurants[0].latitude, restaurants[0].longitude]} zoom={10} scrollWheelZoom className="h-[520px] w-full">
                <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <MapFocus restaurants={restaurants} selected={selectedRestaurantId ? selectedRestaurant : null} />
                {restaurants.map((restaurant) => (
                  <BusinessMapMarker
                    key={restaurant.businessId}
                    position={[restaurant.latitude, restaurant.longitude]}
                    variant="candidate"
                    selected={restaurant.businessId === selectedRestaurant?.businessId}
                    eventHandlers={{ click: () => setSelectedRestaurantId(restaurant.businessId) }}
                  >
                    <Popup>
                      <div className="min-w-[220px] space-y-2">
                        <BusinessPhoto photos={restaurant.photos} alt={`${restaurant.name} 데이터셋 사진`} className="h-24 w-full" compact />
                        <div><strong className="text-sm text-[#17211D]">{restaurant.name}</strong><p className="mt-0.5 text-[11px] text-[#718078]">{restaurant.city}, {restaurant.state} · {restaurant.primaryCategory}</p></div>
                        <DatasetRating stars={restaurant.stars} reviewCount={restaurant.reviewCount} compact />
                        <BusinessAttributeBadges attributes={restaurant.displayAttributes} compact showAddress />
                        <p className="text-[10px] text-[#4F5D56]">추천 연결 리뷰어 {restaurant.matchedReviewerCount.toLocaleString()}명</p>
                      </div>
                    </Popup>
                  </BusinessMapMarker>
                ))}
              </MapContainer>
              <MapLegend className="absolute bottom-6 left-3 z-[500]" items={[{ variant: "candidate", label: "음식점 후보" }]} />
            </div>
          ) : <div className="mt-4 grid h-[320px] place-items-center rounded-xl bg-[#F7F8F5] px-5 text-center text-sm text-[#626D67]">{candidates.length === 0 ? "현재 조건에 맞는 CRM 후보가 없습니다." : "음식점 추천 결과를 불러오고 있거나 좌표가 확인된 후보가 없습니다."}</div>}
          <p className="mt-3 text-[10px] leading-4 text-[#718078]">음식점 공개 좌표를 표시하며 리뷰어의 거주지나 실제 생활권을 의미하지 않습니다.</p>
        </section>

        <aside className="rounded-2xl border border-[#DDE4DF] bg-white p-5">
          <p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">CONTENT CANDIDATES</p><h2 className="mt-1 text-lg font-black">음식점 후보</h2>
          <div className="mt-4 max-h-[570px] space-y-2 overflow-y-auto pr-1">
            {restaurants.map((restaurant) => (
              <article key={restaurant.businessId} className={`rounded-xl border p-4 transition ${restaurant.businessId === selectedRestaurant?.businessId ? "border-[#075C45] bg-[#F0F7F3] shadow-[0_5px_16px_rgba(7,92,69,0.08)]" : "border-[#E2E7E3] hover:border-[#9FBCAE]"}`}>
                <button type="button" onClick={() => setSelectedRestaurantId(restaurant.businessId)} className="w-full text-left">
                  <BusinessPhoto photos={restaurant.photos} alt={`${restaurant.name} 데이터셋 사진`} className="mb-3 h-28 w-full" />
                  <div className="flex items-start justify-between gap-2"><strong className="min-w-0 truncate text-sm">{restaurant.name}</strong><span className="shrink-0 rounded-full bg-[#E7F3ED] px-2 py-1 text-[10px] font-black text-[#075C45]">추천 {restaurant.matchedReviewerCount.toLocaleString()}명</span></div>
                  <p className="mt-1 text-xs text-[#718078]">{restaurant.city}, {restaurant.state} · {restaurant.primaryCategory}</p>
                  <div className="mt-2"><DatasetRating stars={restaurant.stars} reviewCount={restaurant.reviewCount} compact showSource /></div>
                  <div className="mt-2"><BusinessAttributeBadges attributes={restaurant.displayAttributes} compact /></div>
                </button>
              </article>
            ))}
          </div>
        </aside>
      </div>
    </section>
  );
}

function MetricCard({ label, value, note, tone }) { return <article className="rounded-xl border border-[#DDE4DF] bg-white px-5 py-4"><p className="text-xs font-semibold text-[#718078]">{label}</p><p className={`mt-1 text-xl font-black ${tone === "green" ? "text-[#075C45]" : "text-[#17211D]"}`}>{value}</p><p className="mt-1 text-[11px] text-[#8A948F]">{note}</p></article>; }

export default ContentNetworkPage;
