import { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

import { loadRegionalCampaignRestaurants } from "../../data";
import BusinessAttributeBadges from "../business/BusinessAttributeBadges";
import BusinessPhoto from "../business/BusinessPhoto";
import DatasetRating from "../business/DatasetRating";
import BusinessMapMarker, { MapLegend } from "../map/BusinessMapMarker";
import WorkflowActionFooter from "../workflow/WorkflowActionFooter";

function RestaurantFocus({ restaurants, selectedRestaurant }) {
  const map = useMap();
  const focus = selectedRestaurant ?? restaurants[0];
  const key = focus ? `${focus.latitude}:${focus.longitude}` : "";

  useEffect(() => {
    if (focus?.latitude && focus?.longitude) {
      map.setView([focus.latitude, focus.longitude], selectedRestaurant ? 12 : 10);
    }
  }, [focus, key, map, selectedRestaurant]);
  return null;
}

function Step({ number, label, value, active, complete, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-12 rounded-lg border px-3 py-2 text-left transition ${
        active
          ? "border-[#075C45] bg-[#075C45] text-white shadow-sm"
          : complete ? "border-[#B7D8C8] bg-[#EAF3ED]" : "border-[#DDE4DF] bg-white hover:border-[#7FA894]"
      }`}
    >
      <span className={`text-[10px] font-black ${active ? "text-[#BDE2CF]" : "text-[#137A5A]"}`}>{complete ? "✓" : number} · {label}</span>
      <strong className={`mt-0.5 block truncate text-xs ${active ? "text-white" : "text-[#17211D]"}`}>{value}</strong>
    </button>
  );
}

function RegionalCampaignBuilder({
  region,
  targetScope,
  cityKey,
  cityName,
  regions,
  cities,
  onLocationChange,
  candidates,
  riskTypes,
  selectedSignal,
  weekdayPattern,
  onSignalChange,
  onSave,
}) {
  const [activeStep, setActiveStep] = useState(1);
  const [restaurantData, setRestaurantData] = useState(null);
  const [selectedRestaurantId, setSelectedRestaurantId] = useState(null);
  const [selectedRestaurantIds, setSelectedRestaurantIds] = useState(() => new Set());
  const [saving, setSaving] = useState(false);
  const [campaignPurpose, setCampaignPurpose] = useState("핵심 리뷰어 재활성화");
  const [messageTitle, setMessageTitle] = useState("");
  const [messageBody, setMessageBody] = useState("");
  const sampleIdsKey = useMemo(
    () => candidates.map((candidate) => candidate.sampleId).join(","),
    [candidates],
  );

  useEffect(() => {
    let cancelled = false;
    if (!sampleIdsKey) {
      return undefined;
    }
    loadRegionalCampaignRestaurants(region, sampleIdsKey.split(","), targetScope, cityKey)
      .then((data) => {
        if (!cancelled) {
          setRestaurantData({ ...data, requestKey: sampleIdsKey });
          setSelectedRestaurantIds(new Set((data.restaurants ?? []).map((restaurant) => restaurant.businessId)));
        }
      })
      .catch(() => {
        if (!cancelled) setRestaurantData({ available: false, restaurants: [], requestKey: sampleIdsKey });
      });
    return () => {
      cancelled = true;
    };
  }, [cityKey, region, sampleIdsKey, targetScope]);

  const citiesForRegion = useMemo(
    () => cities.filter((city) => city.state === region),
    [cities, region],
  );
  const scopeLabel = targetScope === "city"
    ? `${region} · ${cityName ?? "도시 선택 필요"}`
    : `${region} 전체`;

  function changeScope(nextScope) {
    if (nextScope === "region") {
      onLocationChange("region", region, null);
      return;
    }
    const nextCity = citiesForRegion.find((city) => city.cityKey === cityKey) ?? citiesForRegion[0];
    onLocationChange("city", region, nextCity?.cityKey ?? null);
  }

  function changeRegion(nextRegion) {
    if (targetScope === "region") {
      onLocationChange("region", nextRegion, null);
      return;
    }
    const firstCity = cities.find((city) => city.state === nextRegion);
    onLocationChange("city", nextRegion, firstCity?.cityKey ?? null);
  }

  const restaurants = useMemo(() => {
    if (restaurantData?.requestKey !== sampleIdsKey) return [];
    const uniqueByBusinessId = new Map();
    (restaurantData.restaurants ?? []).forEach((restaurant) => {
      if (!uniqueByBusinessId.has(restaurant.businessId)) {
        uniqueByBusinessId.set(restaurant.businessId, restaurant);
      }
    });
    return [...uniqueByBusinessId.values()];
  }, [restaurantData, sampleIdsKey]);
  const sponsors = useMemo(() => {
    if (restaurantData?.requestKey !== sampleIdsKey) return [];
    return restaurantData.sponsoredRestaurants ?? [];
  }, [restaurantData, sampleIdsKey]);
  const selectedRestaurant = restaurants.find(
    (restaurant) => restaurant.businessId === selectedRestaurantId,
  ) ?? restaurants[0];
  const mappedRestaurants = restaurants.filter(
    (restaurant) => Number.isFinite(restaurant.latitude) && Number.isFinite(restaurant.longitude),
  );
  const goal = selectedSignal === "탐색 활동 축소형"
    ? "새로운 음식점 탐색과 리뷰 작성의 재개"
    : "리뷰 활동 재개와 운영 검토 대상의 우선순위 확인";
  const weekendIntensity = weekdayPattern?.weekendIntensity ?? null;
  const weekdayIntensity = weekendIntensity == null ? null : 1 - weekendIntensity;
  const baselineDelta = weekdayPattern?.baselineDeltaPercentagePoints ?? null;
  const weekdayPatternValue = weekendIntensity == null
    ? "집계 준비 중"
    : `주말 ${(weekendIntensity * 100).toFixed(1)}% · 평일 ${(weekdayIntensity * 100).toFixed(1)}%`;
  const weekdayGuidance = baselineDelta == null
    ? null
    : Math.abs(baselineDelta) < 0.1
      ? "전체 권역과 비슷한 요일 강도입니다."
      : `전체 권역보다 주말 리뷰 강도가 ${Math.abs(baselineDelta).toFixed(1)}%p ${baselineDelta > 0 ? "높습니다" : "낮습니다"}.`;

  function toggleRestaurant(businessId) {
    setSelectedRestaurantIds((current) => {
      const next = new Set(current);
      if (next.has(businessId)) next.delete(businessId);
      else next.add(businessId);
      return next;
    });
  }

  async function saveCampaign() {
    setSaving(true);
    try {
      await onSave({
        actionType: campaignPurpose,
        channels: ["app"],
        businessIds: [...selectedRestaurantIds],
        messageTitle,
        messageBody,
        milestones: [
          { dayOffset: 30, metricCode: "review_writers", metricLabel: "리뷰 작성자 수", observationNote: "비교 관찰" },
          { dayOffset: 60, metricCode: "review_count", metricLabel: "리뷰 수", observationNote: "비교 관찰" },
          { dayOffset: 90, metricCode: "active_reviewers", metricLabel: "활동 리뷰어 수", observationNote: "비교 관찰" },
        ],
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="mt-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] font-black tracking-[0.14em] text-[#137A5A]">CAMPAIGN WORKSPACE</p>
          <h2 className="mt-1 text-xl font-black text-[#17211D]">{scopeLabel}</h2>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-[#626D67]">
            실제 CRM 후보와 이미 산출된 음식점 추천을 사용합니다. 발송 기능이 아닌 운영 검토·명단 저장 단계입니다.
          </p>
        </div>
        <span className="rounded-full border border-[#B7D8C8] bg-white px-3 py-1.5 text-xs font-bold text-[#137A5A]">
          규칙 기반 운영 가설 · A/B 검증 필요
        </span>
      </div>

      <div className="mt-4 grid gap-2 md:grid-cols-4">
        <Step number="1" label="대상 지역" value={scopeLabel} active={activeStep === 1} complete={activeStep > 1} onClick={() => setActiveStep(1)} />
        <Step number="2" label="대상 조건" value={`${selectedSignal} · ${candidates.length.toLocaleString()}명`} active={activeStep === 2} complete={activeStep > 2} onClick={() => setActiveStep(2)} />
        <Step number="3" label="콘텐츠 선택" value={`${selectedRestaurantIds.size} / ${restaurants.length}곳`} active={activeStep === 3} complete={activeStep > 3} onClick={() => setActiveStep(3)} />
        <Step number="4" label="검토·저장" value="30 · 60 · 90일" active={activeStep === 4} complete={false} onClick={() => setActiveStep(4)} />
      </div>

      <div className="mt-3 min-h-[430px] rounded-2xl border border-[#DDE4DF] bg-white p-4 shadow-[0_8px_24px_rgba(23,33,29,0.04)]">
        {activeStep === 1 && (
          <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
            <div>
              <p className="text-xs font-black tracking-[0.12em] text-[#137A5A]">STEP 1</p>
              <h3 className="mt-2 text-xl font-black">캠페인 대상 지역 선택</h3>
              <p className="mt-2 text-sm leading-6 text-[#626D67]">권역 전체 또는 표본 기준을 충족한 도시를 선택합니다. 선택 범위는 CRM 후보, 요일 집계, 음식점 후보와 저장 운영안에 동일하게 적용됩니다.</p>
              <div className="mt-5 grid gap-3 rounded-xl border border-[#DDE4DF] bg-[#FAFBFA] p-4 md:grid-cols-[220px_1fr_1fr]">
                <div>
                  <span className="text-[11px] font-black text-[#59675F]">대상 범위</span>
                  <div className="mt-2 grid grid-cols-2 rounded-lg border border-[#C9D5CE] bg-white p-1">
                    <button type="button" onClick={() => changeScope("region")} className={`min-h-9 rounded-md text-xs font-black ${targetScope === "region" ? "bg-[#075C45] text-white" : "text-[#65726B]"}`}>권역 전체</button>
                    <button type="button" onClick={() => changeScope("city")} className={`min-h-9 rounded-md text-xs font-black ${targetScope === "city" ? "bg-[#075C45] text-white" : "text-[#65726B]"}`}>도시</button>
                  </div>
                </div>
                <label className="text-[11px] font-black text-[#59675F]">권역
                  <select value={region} onChange={(event) => changeRegion(event.target.value)} className="mt-2 min-h-11 w-full rounded-lg border border-[#C9D5CE] bg-white px-3 text-sm">
                    {regions.map((item) => <option key={item} value={item}>{item}</option>)}
                  </select>
                </label>
                <label className="text-[11px] font-black text-[#59675F]">도시
                  <select value={cityKey ?? ""} disabled={targetScope !== "city" || citiesForRegion.length === 0} onChange={(event) => onLocationChange("city", region, event.target.value)} className="mt-2 min-h-11 w-full rounded-lg border border-[#C9D5CE] bg-white px-3 text-sm disabled:bg-[#EEF1EF] disabled:text-[#9AA39E]">
                    {targetScope !== "city" && <option value="">권역 전체 적용</option>}
                    {targetScope === "city" && citiesForRegion.length === 0 && <option value="">선택 가능한 도시 없음</option>}
                    {citiesForRegion.map((city) => <option key={city.cityKey} value={city.cityKey}>{city.city} · CRM {city.crmTargets.toLocaleString()}명</option>)}
                  </select>
                </label>
              </div>
              <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <Insight title="대상 지역" value={scopeLabel} />
                <Insight title="CRM 후보" value={`${candidates.length.toLocaleString()}명`} />
                <Insight title="캠페인 성격" value="운영 가설 · A/B 검증 필요" />
                <Insight title="리뷰 요일 강도" value={weekdayPatternValue} />
              </div>
              {weekdayPattern && (
                <div className="mt-4 rounded-xl border border-[#CFE3D8] bg-[#F0F7F3] px-4 py-3 text-sm leading-6 text-[#365D4D]">
                  <strong className="text-[#075C45]">{weekdayPattern.peakDay}요일 리뷰가 가장 많습니다.</strong>{" "}
                  {weekdayGuidance} 캠페인 시작일을 정할 때 참고하되, 캠페인 성과를 예측하는 지표는 아닙니다.
                </div>
              )}
            </div>
            <div className="rounded-xl bg-[#F0F7F3] p-5"><p className="text-sm font-black text-[#075C45]">선정 원칙</p><ul className="mt-3 space-y-3 text-xs leading-5 text-[#4B665B]"><li>• 활동 권역과 CRM 상위 20% 조건을 사용합니다.</li><li>• 관리자가 ‘이번엔 제외’로 판단한 리뷰어는 제외합니다.</li><li>• 효과 수치를 사전에 약속하지 않고 비교 관찰합니다.</li></ul></div>
          </div>
        )}

        {activeStep === 2 && (
          <div><p className="text-xs font-black tracking-[0.12em] text-[#137A5A]">STEP 2</p><h3 className="mt-2 text-xl font-black">대상 조건 선택</h3><p className="mt-2 text-sm text-[#626D67]">한 가지 위험 신호에 집중하거나 전체 CRM 후보를 유지할 수 있습니다.</p><div className="mt-5 flex flex-wrap gap-2">{["전체", ...riskTypes].map((signal) => <button key={signal} type="button" onClick={() => onSignalChange(signal)} className={`min-h-10 rounded-full border px-4 text-xs font-black ${selectedSignal === signal ? "border-[#075C45] bg-[#075C45] text-white" : "border-[#DDE4DF] text-[#626D67] hover:border-[#137A5A]"}`}>{signal}</button>)}</div><div className="mt-6 grid gap-3 sm:grid-cols-3"><Insight title="선택 조건" value={selectedSignal} /><Insight title="현재 후보" value={`${candidates.length.toLocaleString()}명`} /><Insight title="운영 가설" value={goal} /></div><div className="mt-5 rounded-xl border border-[#E2E7E3] p-4"><p className="text-xs font-black text-[#075C45]">관찰할 활동 근거</p><p className="mt-2 text-sm text-[#626D67]">리뷰 수 · 활동 월 · 고유 음식점 · 리뷰 공백 · 신규 음식점 리뷰</p></div></div>
        )}

        {activeStep === 3 && (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
            <div>
              <div className="flex items-end justify-between">
                <div><p className="text-xs font-black tracking-[0.12em] text-[#137A5A]">STEP 3</p><h3 className="mt-2 text-xl font-black">캠페인 콘텐츠 선택</h3></div>
                <span className="text-xs font-bold text-[#075C45]">{selectedRestaurantIds.size} / {restaurants.length}곳 선택</span>
              </div>
              {mappedRestaurants.length > 0 ? (
                <div className="relative mt-3 overflow-hidden rounded-xl border border-[#DDE4DF]">
                  <MapContainer center={[mappedRestaurants[0].latitude, mappedRestaurants[0].longitude]} zoom={10} scrollWheelZoom className="h-[350px] w-full">
                    <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                    <RestaurantFocus restaurants={mappedRestaurants} selectedRestaurant={selectedRestaurant} />
                    {mappedRestaurants.map((restaurant) => {
                      const checked = selectedRestaurantIds.has(restaurant.businessId);
                      const focused = restaurant.businessId === selectedRestaurant?.businessId;
                      return (
                        <BusinessMapMarker
                          key={restaurant.businessId}
                          position={[restaurant.latitude, restaurant.longitude]}
                          variant={checked ? "candidate" : "inactive"}
                          selected={focused}
                          eventHandlers={{ click: () => setSelectedRestaurantId(restaurant.businessId) }}
                        >
                          <Popup>
                            <div className="min-w-[210px] space-y-2">
                              <BusinessPhoto photos={restaurant.photos} alt={`${restaurant.name} 데이터셋 사진`} className="h-24 w-full" compact />
                              <div><strong className="text-sm text-[#17211D]">{restaurant.name}</strong><p className="mt-0.5 text-[11px] text-[#718078]">{restaurant.city}, {restaurant.state} · {restaurant.primaryCategory}</p></div>
                              <DatasetRating stars={restaurant.stars} reviewCount={restaurant.reviewCount} compact />
                              <BusinessAttributeBadges attributes={restaurant.displayAttributes} compact showAddress />
                            </div>
                          </Popup>
                        </BusinessMapMarker>
                      );
                    })}
                  </MapContainer>
                  <MapLegend className="absolute bottom-6 left-3 z-[500]" items={[{ variant: "candidate", label: "캠페인 선택" }, { variant: "inactive", label: "선택 제외" }]} />
                </div>
              ) : <p className="mt-4 rounded-xl bg-[#F7F8F5] p-5 text-sm text-[#626D67]">현재 후보 집단에 연결된 음식점 추천 결과가 없습니다.</p>}
            </div>
            <div className="max-h-[430px] space-y-1.5 overflow-y-auto pr-1">
              {sponsors.length > 0 && (
                <>
                  <p className="px-1 text-[9px] font-black tracking-[0.1em] text-[#8A6116]">스폰서 매장 · {sponsors.length}곳</p>
                  {sponsors.map((sponsor) => (
                    <article key={sponsor.businessId} className="rounded-lg border border-[#EF9F27] bg-[#FAEEDA] p-2.5">
                      <div className="flex items-start gap-3">
                        <div className="grid min-w-0 flex-1 grid-cols-[76px_minmax(0,1fr)] gap-3 text-left">
                          <BusinessPhoto photos={sponsor.photos} alt={`${sponsor.name} 데이터셋 사진`} className="h-[68px] w-[76px]" compact />
                          <span className="min-w-0">
                            <span className="flex items-center gap-1.5">
                              <strong className="truncate text-sm">{sponsor.name}</strong>
                              <span className="shrink-0 rounded bg-[#EF9F27] px-1.5 py-0.5 text-[9px] font-bold text-[#412402]">스폰서</span>
                            </span>
                            <span className="mt-1 block text-[11px] text-[#8A6116]">{sponsor.city}, {sponsor.state} · {sponsor.primaryCategory}</span>
                            <span className="mt-0.5 block text-[10px] text-[#63380C]">캠페인 노출 기간 ~ {sponsor.sponsorshipEndDate}</span>
                            <span className="mt-2 block"><DatasetRating stars={sponsor.stars} reviewCount={sponsor.reviewCount} compact /></span>
                          </span>
                        </div>
                      </div>
                    </article>
                  ))}
                  <p className="px-1 pb-1 pt-1 text-[9px] font-black tracking-[0.1em] text-[#626D67]">로컬 맛집 · {selectedRestaurantIds.size} / {restaurants.length}곳 선택</p>
                </>
              )}
              {restaurants.map((restaurant) => (
                <article key={restaurant.businessId} className={`rounded-lg border p-2.5 transition ${restaurant.businessId === selectedRestaurant?.businessId ? "border-[#075C45] bg-[#F2F8F5] shadow-[0_5px_16px_rgba(7,92,69,0.08)]" : "border-[#E2E7E3]"}`}>
                  <div className="flex items-start gap-3">
                    <input type="checkbox" checked={selectedRestaurantIds.has(restaurant.businessId)} onChange={() => toggleRestaurant(restaurant.businessId)} aria-label={`${restaurant.name} 캠페인 선택`} className="mt-1 h-4 w-4 accent-[#075C45]" />
                    <button type="button" onClick={() => setSelectedRestaurantId(restaurant.businessId)} className="grid min-w-0 flex-1 grid-cols-[76px_minmax(0,1fr)] gap-3 text-left">
                      <BusinessPhoto photos={restaurant.photos} alt={`${restaurant.name} 데이터셋 사진`} className="h-[68px] w-[76px]" compact />
                      <span className="min-w-0">
                      <span className="flex items-center gap-1.5">
                        <strong className="truncate text-sm">{restaurant.name}</strong>
                        {restaurant.reviewSupplyChangeRate != null && restaurant.reviewSupplyChangeRate < -0.15 && (
                          <span className="shrink-0 rounded bg-[#F0997B] px-1.5 py-0.5 text-[9px] font-bold text-[#4A1B0C]">리뷰 공급 감소</span>
                        )}
                      </span>
                      <span className="mt-1 block text-[11px] text-[#718078]">{restaurant.city}, {restaurant.state} · {restaurant.primaryCategory}</span>
                      {restaurant.reviewSupplyChangeRate != null && restaurant.reviewSupplyChangeRate < -0.15 && (
                        <span className="mt-0.5 block text-[10px] text-[#9F4A38]">이 매장 리뷰 {(restaurant.reviewSupplyChangeRate * 100).toFixed(0)}% (2017 → 2018)</span>
                      )}
                      <span className="mt-2 block"><DatasetRating stars={restaurant.stars} reviewCount={restaurant.reviewCount} compact /></span>
                      </span>
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        )}

        {activeStep === 4 && (
          <div>
            <p className="text-xs font-black tracking-[0.12em] text-[#137A5A]">STEP 4</p><h3 className="mt-2 text-xl font-black">검토 및 저장</h3>
            <div className="mt-5 grid gap-3 md:grid-cols-4"><Insight title="대상 지역" value={scopeLabel} /><Insight title="위험 조건" value={selectedSignal} /><Insight title="대상 리뷰어" value={`${candidates.length.toLocaleString()}명`} /><Insight title="선택 음식점" value={`${selectedRestaurantIds.size}곳`} /></div>
            <div className="mt-5 grid gap-4 lg:grid-cols-2"><label className="text-xs font-bold text-[#59675F]">캠페인 목적<select value={campaignPurpose} onChange={(event) => setCampaignPurpose(event.target.value)} className="mt-2 min-h-11 w-full rounded-lg border border-[#DDE4DF] bg-white px-3"><option>핵심 리뷰어 재활성화</option><option>신규 핵심 리뷰어 유입</option><option>지역 콘텐츠 다양화</option><option>지역 쿠폰 이벤트 검토</option></select></label><label className="text-xs font-bold text-[#59675F]">메시지 제목<input value={messageTitle} onChange={(event) => setMessageTitle(event.target.value)} placeholder="운영 검토용 제목" className="mt-2 min-h-11 w-full rounded-lg border border-[#DDE4DF] px-3" /></label></div>
            {campaignPurpose === "지역 쿠폰 이벤트 검토" && (
              <p className="mt-4 rounded-lg bg-[#FFF7E8] px-4 py-3 text-xs leading-5 text-[#8A5A12]">
                이 캠페인은 쿠폰을 발급하지 않습니다. 저장된 명단은 B2C팀 전달용 운영 검토 자료입니다.
              </p>
            )}
            <label className="mt-4 block text-xs font-bold text-[#59675F]">메시지 초안<textarea value={messageBody} onChange={(event) => setMessageBody(event.target.value)} placeholder="실제 발송되지 않는 운영 검토용 초안" className="mt-2 min-h-24 w-full rounded-lg border border-[#DDE4DF] p-3" /></label>
            <div className="mt-6 grid gap-5 lg:grid-cols-2"><div className="rounded-xl border border-[#DDE4DF] p-5"><p className="text-sm font-black">기대효과</p><p className="mt-3 text-sm leading-6 text-[#626D67]">{goal} 여부를 검증합니다. 리뷰 증가나 복귀를 확정 효과로 표현하지 않습니다.</p><p className="mt-4 rounded-lg bg-[#FCEFEA] p-3 text-xs leading-5 text-[#9F4A38]">캠페인 명단 저장은 메시지 발송이 아니며 실제 실행 전 운영자 검토가 필요합니다.</p></div><div className="rounded-xl border border-[#DDE4DF] p-5"><p className="text-sm font-black">측정 계획</p><div className="mt-4 grid grid-cols-3 gap-2">{[["30일", "작성자 수"], ["60일", "리뷰 수"], ["90일", "활동 리뷰어"]].map(([period, metric]) => <div key={period} className="rounded-lg bg-[#F0F7F3] p-3 text-center"><strong className="text-sm text-[#075C45]">{period}</strong><span className="mt-1 block text-[11px] text-[#626D67]">{metric}</span></div>)}</div><p className="mt-3 text-xs leading-5 text-[#718078]">가능하면 비교군과 신규 음식점 리뷰를 함께 관찰합니다.</p></div></div>
          </div>
        )}
      </div>

      <WorkflowActionFooter
        summary={`대상 리뷰어 ${candidates.length.toLocaleString()}명 · 음식점 ${selectedRestaurantIds.size}곳`}
        detail={activeStep === 4 ? "측정 계획을 확인한 뒤 운영 검토 명단으로 저장합니다." : `${activeStep}/4 단계 · 선택 내용은 다음 단계에 유지됩니다.`}
        secondaryAction={activeStep > 1 ? <button type="button" onClick={() => setActiveStep((step) => step - 1)} className="min-h-10 rounded-lg border border-[#B7D8C8] px-4 text-xs font-bold text-[#075C45]">이전</button> : null}
        primaryAction={activeStep < 4 ? <button type="button" onClick={() => setActiveStep((step) => step + 1)} disabled={candidates.length === 0} className="min-h-11 rounded-xl bg-[#075C45] px-5 text-sm font-black text-white disabled:bg-[#B3BBB6]">다음 단계 →</button> : <button type="button" onClick={saveCampaign} disabled={saving || candidates.length === 0} className="min-h-11 rounded-xl bg-[#075C45] px-5 text-sm font-black text-white disabled:bg-[#B3BBB6]">{saving ? "저장 중…" : "운영 검토 명단 저장"}</button>}
      />
    </section>
  );
}

function Insight({ title, value }) {
  return <div className="rounded-lg bg-[#EAF3ED] p-4"><p className="text-xs font-bold text-[#137A5A]">{title}</p><p className="mt-2 text-sm leading-5 text-[#356A78]">{value}</p></div>;
}

export default RegionalCampaignBuilder;
