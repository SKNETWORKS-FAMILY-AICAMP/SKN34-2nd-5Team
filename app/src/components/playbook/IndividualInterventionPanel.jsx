import { useEffect, useMemo, useState } from "react";
import { MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import { Link } from "react-router";
import "leaflet/dist/leaflet.css";

import BusinessAttributeBadges from "../business/BusinessAttributeBadges";
import BusinessPhoto from "../business/BusinessPhoto";
import DatasetRating from "../business/DatasetRating";
import BusinessMapMarker, { MapLegend } from "../map/BusinessMapMarker";
import WorkflowActionFooter from "../workflow/WorkflowActionFooter";

function RecommendationFocus({ restaurants, focusedId }) {
  const map = useMap();
  const selected = restaurants.find((restaurant) => restaurant.businessId === focusedId) ?? restaurants[0];
  const key = selected ? `${selected.latitude}:${selected.longitude}` : "";
  useEffect(() => {
    if (selected?.latitude && selected?.longitude) map.setView([selected.latitude, selected.longitude], 12);
  }, [key, map, selected]);
  return null;
}

function IndividualInterventionPanel({ reviewer, recommendationData, strategy, onSave }) {
  const restaurants = useMemo(
    () => (recommendationData?.recommendations ?? []).filter((item) => Number.isFinite(item.latitude) && Number.isFinite(item.longitude)),
    [recommendationData],
  );
  const initialRestaurantIds = restaurants.slice(0, 3).map((item) => item.businessId);
  const [focusedId, setFocusedId] = useState(initialRestaurantIds[0] ?? null);
  const [selectedIds, setSelectedIds] = useState(null);
  const [saving, setSaving] = useState(false);
  const [actionType, setActionType] = useState(strategy.secondary || "운영자 직접 확인");
  const [channels, setChannels] = useState(["app"]);
  const [messageBody, setMessageBody] = useState("");
  const activeSelectedIds = selectedIds ?? initialRestaurantIds;
  const selectedRestaurants = restaurants.filter((item) => activeSelectedIds.includes(item.businessId));
  const radiusContext = recommendationData?.radiusContext;
  const isExploration = reviewer.riskType === "탐색 활동 축소형";
  const effectiveDecision = reviewer.managerDecision ?? reviewer.effectiveDecision;

  function toggleRestaurant(businessId) {
    setFocusedId(businessId);
    setSelectedIds((current) => {
      const selected = current ?? initialRestaurantIds;
      return selected.includes(businessId)
        ? selected.filter((id) => id !== businessId)
        : [...selected, businessId];
    });
  }

  async function saveIntervention() {
    setSaving(true);
    try {
      await onSave({
        actionType,
        channels,
        businessIds: activeSelectedIds,
        messageTitle: `${strategy.title} 운영안`,
        messageBody,
        milestones: [
          { dayOffset: 30, metricCode: "review_restart", metricLabel: "리뷰 재개 여부", observationNote: "리뷰 1건 이상" },
          { dayOffset: 60, metricCode: "active_month", metricLabel: "활동 월 변화", observationNote: "활동 월 확인" },
          { dayOffset: 90, metricCode: "continuity", metricLabel: "지속 여부", observationNote: "지속 활동 확인" },
        ],
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="mt-5">
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-[#B7D8C8] bg-white px-4 py-3">
        <span className="grid h-11 w-11 place-items-center rounded-full bg-[#E3F1EA] text-sm font-black text-[#075C45]">360</span>
        <div className="min-w-0 flex-1"><p className="break-all text-lg font-black text-[#17211D]">{reviewer.userId}</p><p className="mt-1 text-xs text-[#718078]">{reviewer.region ? `${reviewer.region} · ${reviewer.topCity ?? "대표 활동 도시"}` : "활동 권역 확인 불가"}</p></div>
        <Badge label="우선순위" value={`${reviewer.priorityRank}위`} />
        <Badge label="모델 판단" value={reviewer.modelJudgment} />
        <Badge label="관리자 판단" value={effectiveDecision} emphasis />
        <span className="max-w-[220px] text-[10px] leading-4 text-[#718078]">모델 점수는 위험 순위 지표이며 확률이 아닙니다.</span>
      </div>

      <div className="mt-4 grid items-start gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(520px,0.95fr)]">
        <div className="rounded-2xl border border-[#DDE4DF] bg-white p-5">
          <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">RECOMMENDATION MAP</p><h2 className="mt-1 text-lg font-black">개인 맞춤 음식점 후보</h2><p className="mt-1 text-xs leading-5 text-[#626D67]">관심 카테고리 기반 사업장 후보이며 리뷰 활동 반경이나 생활권을 뜻하지 않습니다.</p></div><span className="rounded-full bg-[#EEF7F2] px-3 py-1 text-xs font-black text-[#075C45]">{restaurants.length}곳</span></div>
          {radiusContext && (
            <div className="mt-4 rounded-xl border border-[#B7D8C8] bg-[#F0F7F3] px-4 py-3">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
                <strong className="text-[#075C45]">주 활동 권역 기준</strong>
                <span className="text-[#626D67]">전체 활동 P90 {radiusContext.observedP90RadiusKm.toLocaleString()}km</span>
                <span className="font-black text-[#9F4A38]">→</span>
                <span className="font-bold text-[#17211D]">주 권역 P90 {radiusContext.primaryClusterP90RadiusKm.toLocaleString()}km</span>
                <span className="rounded-full bg-white px-2 py-0.5 font-bold text-[#075C45]">실제 검색 {radiusContext.appliedSearchRadiusKm.toLocaleString()}km</span>
              </div>
              <p className="mt-1 text-[10px] leading-4 text-[#626D67]">
                50km 기준 {radiusContext.activityClusterCount}개 활동 권역 중 주 권역 {radiusContext.primaryClusterBusinessCount}곳을 기준으로 계산했습니다.
                {radiusContext.multiRegionActivity && ` 원거리 ${radiusContext.remoteRegionCount}개 권역·${radiusContext.travelOutlierCount}곳은 추천 중심에서 분리했습니다.`}
                {radiusContext.radiusCapApplied ? " 주 권역 P90이 넓어 검색에는 50km 상한을 적용했습니다." : " 후보가 부족할 때만 최대 50km까지 단계적으로 확장합니다."}
              </p>
            </div>
          )}
          {restaurants.length > 0 ? (
            <div className="relative mt-4 overflow-hidden rounded-xl">
              <MapContainer center={[restaurants[0].latitude, restaurants[0].longitude]} zoom={12} scrollWheelZoom className="h-[360px] w-full">
                <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <RecommendationFocus restaurants={restaurants} focusedId={focusedId} />
                {restaurants.map((restaurant) => (
                  <BusinessMapMarker
                    key={restaurant.businessId}
                    position={[restaurant.latitude, restaurant.longitude]}
                    variant="recommendation"
                    selected={activeSelectedIds.includes(restaurant.businessId)}
                    eventHandlers={{ click: () => setFocusedId(restaurant.businessId) }}
                  >
                    <Popup>
                      <div className="min-w-[210px] space-y-2">
                        <BusinessPhoto photos={restaurant.photos} alt={`${restaurant.name} 데이터셋 사진`} className="h-24 w-full" compact />
                        <div><strong className="text-sm text-[#17211D]">{restaurant.name}</strong><p className="mt-0.5 text-[11px] text-[#718078]">{restaurant.city}, {restaurant.state} · {restaurant.primaryCategory}</p></div>
                        <DatasetRating stars={restaurant.stars} reviewCount={restaurant.reviewCount} compact />
                        <DistanceBadge restaurant={restaurant} />
                        <BusinessAttributeBadges attributes={restaurant.displayAttributes} compact showAddress />
                      </div>
                    </Popup>
                  </BusinessMapMarker>
                ))}
              </MapContainer>
              <MapLegend className="absolute bottom-6 left-3 z-[500]" items={[{ variant: "recommendation", label: "맞춤 추천 후보" }]} />
            </div>
          ) : <p className="mt-4 rounded-xl bg-[#F7F8F5] p-5 text-sm text-[#626D67]">현재 연결된 추천 음식점 좌표가 없습니다.</p>}
          <div className="mt-4 grid gap-2 md:grid-cols-3">
            {restaurants.slice(0, 3).map((restaurant) => (
              <button key={restaurant.businessId} type="button" onClick={() => toggleRestaurant(restaurant.businessId)} className={`relative rounded-xl border p-3 text-left transition ${activeSelectedIds.includes(restaurant.businessId) ? "border-[#075C45] bg-[#F0F7F3] shadow-[0_5px_16px_rgba(7,92,69,0.08)]" : "border-[#E2E7E3] hover:border-[#9FBCAE]"}`}>
                <span className={`absolute right-5 top-5 z-10 grid h-6 w-6 place-items-center rounded-md border text-xs font-black shadow-sm ${activeSelectedIds.includes(restaurant.businessId) ? "border-[#075C45] bg-[#075C45] text-white" : "border-white bg-white text-transparent"}`}>✓</span>
                <BusinessPhoto photos={restaurant.photos} alt={`${restaurant.name} 데이터셋 사진`} className="mb-2 h-20 w-full" compact />
                <strong className="block truncate text-xs">{restaurant.name}</strong>
                <span className="mt-1 block truncate text-[10px] text-[#718078]">{restaurant.primaryCategory} · {restaurant.city}</span>
                <span className="mt-2 block"><DatasetRating stars={restaurant.stars} reviewCount={restaurant.reviewCount} compact /></span>
                <span className="mt-2 block"><DistanceBadge restaurant={restaurant} /></span>
                <span className="mt-2 block"><BusinessAttributeBadges attributes={restaurant.displayAttributes} compact /></span>
              </button>
            ))}
          </div>
        </div>

        <aside className="overflow-hidden rounded-2xl border border-[#DDE4DF] bg-white shadow-[0_8px_24px_rgba(23,33,29,0.05)]">
          <div className="border-b border-[#DDE4DF] bg-white px-5 py-4"><p className="text-[10px] font-black tracking-[0.14em] text-[#137A5A]">ACTION PLAN</p><h2 className="mt-1 text-lg font-black text-[#17211D]">{strategy.title}</h2><p className="mt-1 text-[11px] leading-5 text-[#626D67]">관리자 판단 ‘{effectiveDecision}’을 기준으로 실행 가능한 운영안을 구성합니다.</p></div>
          <div className="p-5">
            <NumberedSection number="1" title="왜 이 액션인가"><ul className="space-y-1.5 text-xs leading-5 text-[#4F5D56]"><li>• {reviewer.coreChange}</li><li>• 핵심 위험 신호: {reviewer.riskType}</li><li>• {strategy.description}</li></ul></NumberedSection>
            <NumberedSection number="2" title="대표 실행안 선택"><div className="grid gap-2 sm:grid-cols-2">{[strategy.secondary || "관리자 검토", "테마별 리스트 큐레이션", "리뷰 리마인더", "운영자 직접 확인"].map((item) => <ChoiceCard key={item} active={actionType === item} onClick={() => setActionType(item)}>{item}</ChoiceCard>)}</div></NumberedSection>
            <NumberedSection number="3" title="채널 선택" note="다중 선택 가능"><div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{[["app", "앱 메시지"], ["email", "이메일"], ["push", "푸시"], ["operator", "운영자 접촉"]].map(([key, label]) => <ChoiceCard key={key} active={channels.includes(key)} onClick={() => setChannels((current) => current.includes(key) ? current.filter((item) => item !== key) : [...current, key])}>{label}</ChoiceCard>)}</div></NumberedSection>
            <NumberedSection number="4" title="선택 콘텐츠" note={`${selectedRestaurants.length}곳 저장`}>
              {selectedRestaurants.length > 0 ? <div className="space-y-2">{selectedRestaurants.map((restaurant) => <SelectedBusinessRow key={restaurant.businessId} restaurant={restaurant} onRemove={() => toggleRestaurant(restaurant.businessId)} />)}</div> : <p className="rounded-lg bg-[#FFF7E8] px-3 py-3 text-xs font-bold text-[#8A5A08]">왼쪽 후보에서 한 곳 이상 선택하세요.</p>}
            </NumberedSection>
            <NumberedSection number="5" title="메시지 초안"><textarea value={messageBody} onChange={(event) => setMessageBody(event.target.value)} placeholder="발송되지 않는 운영 검토용 메시지 초안" className="min-h-20 w-full resize-none rounded-lg border border-[#DDE4DF] p-3 text-xs leading-5 outline-none focus:border-[#075C45]" /></NumberedSection>
            <div className="grid gap-3 pt-4 sm:grid-cols-2">
              <CompactPlan title="기대효과 · 검증 가설"><p>{isExploration ? "신규 음식점 탐색과 리뷰 작성" : "리뷰 재개와 활동 월 변화"} 여부를 관찰합니다. 예상 결과를 사전에 확정하지 않습니다.</p></CompactPlan>
              <CompactPlan title="30·60·90일 측정 계획"><div className="grid grid-cols-3 gap-1">{[["30일", "재개"], ["60일", "활동 월"], ["90일", "지속"]].map(([period, metric]) => <div key={period} className="rounded-md bg-white p-2 text-center"><strong className="block text-[10px] text-[#075C45]">{period}</strong><span className="text-[9px] text-[#626D67]">{metric}</span></div>)}</div></CompactPlan>
            </div>
          </div>
        </aside>
      </div>

      <WorkflowActionFooter summary={`관리자 판단 · ${effectiveDecision}`} detail={`선택 음식점 ${selectedRestaurants.length}곳과 실행안을 한 명의 운영 대상 명단으로 저장합니다.`} secondaryAction={<Link to={`/reviewers/${reviewer.userId}`} className="flex min-h-10 items-center rounded-lg border border-[#B7D8C8] px-4 text-xs font-bold text-[#075C45]">판단 수정</Link>} primaryAction={<button type="button" onClick={saveIntervention} disabled={saving || activeSelectedIds.length === 0 || channels.length === 0} className="min-h-11 rounded-xl bg-[#075C45] px-5 text-sm font-black text-white disabled:bg-[#B3BBB6]">{saving ? "저장 중…" : "핵심 리뷰어 관리 명단에 저장"}</button>} />
    </section>
  );
}

function Badge({ label, value, emphasis }) { return <div className={`rounded-xl px-3 py-2 ${emphasis ? "bg-[#075C45] text-white" : "bg-[#F1F4F1]"}`}><p className={`text-[9px] font-bold ${emphasis ? "text-white/60" : "text-[#718078]"}`}>{label}</p><p className="mt-0.5 whitespace-nowrap text-xs font-black">{value}</p></div>; }
function NumberedSection({ number, title, note, children }) { return <section className="border-b border-[#EDF0EE] py-4 first:pt-0"><div className="mb-3 flex items-center gap-2"><span className="grid h-6 w-6 place-items-center rounded-full bg-[#E3F1EA] text-[10px] font-black text-[#075C45]">{number}</span><p className="text-xs font-black text-[#17211D]">{title}</p>{note && <span className="ml-auto text-[10px] font-bold text-[#718078]">{note}</span>}</div>{children}</section>; }
function ChoiceCard({ children, active, onClick }) { return <button type="button" onClick={onClick} className={`flex min-h-10 items-center gap-2 rounded-lg border px-3 text-left text-[10px] font-bold transition ${active ? "border-[#075C45] bg-[#E7F3ED] text-[#075C45]" : "border-[#DDE4DF] bg-white text-[#4F5D56] hover:border-[#9FBCAE]"}`}><span className={`grid h-4 w-4 place-items-center rounded border text-[9px] ${active ? "border-[#075C45] bg-[#075C45] text-white" : "border-[#B9C4BE] text-transparent"}`}>✓</span>{children}</button>; }
function CompactPlan({ title, children }) { return <section className="rounded-xl border border-[#DDE4DF] bg-[#F7FAF8] p-3"><p className="mb-2 text-[10px] font-black text-[#075C45]">{title}</p><div className="text-[10px] leading-4 text-[#4F5D56]">{children}</div></section>; }
function SelectedBusinessRow({ restaurant, onRemove }) { const url = `https://www.yelp.com/search?find_desc=${encodeURIComponent(restaurant.name)}&find_loc=${encodeURIComponent(`${restaurant.city}, ${restaurant.state}`)}`; return <div className="grid grid-cols-[64px_minmax(0,1fr)_auto] items-center gap-3 rounded-lg border border-[#E2E7E3] bg-white p-2"><BusinessPhoto photos={restaurant.photos} alt={`${restaurant.name} 데이터셋 사진`} className="h-12 w-16" compact /><div className="min-w-0"><p className="truncate text-xs font-black">{restaurant.name}</p><div className="mt-1 flex flex-wrap items-center gap-2"><DatasetRating stars={restaurant.stars} reviewCount={restaurant.reviewCount} compact /><DistanceBadge restaurant={restaurant} /></div></div><div className="flex flex-col items-end gap-1"><a href={url} target="_blank" rel="noreferrer" className="text-[9px] font-black text-[#075C45] underline">Yelp 검색</a><button type="button" onClick={onRemove} className="text-[9px] font-bold text-[#9F4A38]">제외</button></div></div>; }
function DistanceBadge({ restaurant }) { const core = restaurant.distanceBand === "core"; return <span className={`inline-flex rounded-full px-2 py-1 text-[9px] font-black ${core ? "bg-[#E7F3ED] text-[#075C45]" : "bg-[#FFF1ED] text-[#9F4A38]"}`}>{restaurant.distanceKm.toLocaleString()}km · {core ? "핵심 활동권" : "확장 후보"}</span>; }

export default IndividualInterventionPanel;
