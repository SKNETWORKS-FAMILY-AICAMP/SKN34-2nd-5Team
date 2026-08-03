import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";

import DataModeBadge from "../components/DataModeBadge";
import Skeleton from "../components/common/Skeleton";
import ErrorState from "../components/common/ErrorState";
import RegionalBubbleMap from "../components/regional/RegionalBubbleMap";
import RegionalInsightPanel from "../components/regional/RegionalInsightPanel";
import RegionalTravelRange from "../components/regional/RegionalTravelRange";
import WorkflowHeader from "../components/workflow/WorkflowHeader";
import { useOperationsSummary } from "../context/operations-context";
import { loadRegionalDerivedContext, loadRegionalRisk } from "../data";

function RegionalRiskPage() {
  const operationsSummary = useOperationsSummary();
  const [searchParams, setSearchParams] = useSearchParams();
  const [regionalRisk, setRegionalRisk] = useState(null);
  const [error, setError] = useState(null);
  const [hoveredRegion, setHoveredRegion] = useState(null);
  const [derivedContext, setDerivedContext] = useState(null);
  const [mapLayer, setMapLayer] = useState("supply");
  const viewMode = searchParams.get("view") === "travel" ? "travel" : "map";

  useEffect(() => {
    let cancelled = false;

    loadRegionalRisk()
      .then((data) => {
        if (!cancelled) setRegionalRisk(data);
      })
      .catch((loadError) => {
        if (!cancelled) setError(loadError.message);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadRegionalDerivedContext()
      .then((data) => {
        if (!cancelled && data.available) setDerivedContext(data);
      })
      .catch(() => {
        // Optional v05 data must not block the existing regional screen.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const regions = useMemo(() => {
    if (!regionalRisk) return [];
    const supplyByRegion = new Map(
      (derivedContext?.regions ?? []).map((region) => [region.region, region]),
    );
    return regionalRisk.regions
      .map((region) => ({ ...region, ...supplyByRegion.get(region.region) }))
      .sort((first, second) => (first.reviewSupplyChangeRate ?? 0) - (second.reviewSupplyChangeRate ?? 0));
  }, [derivedContext, regionalRisk]);

  const defaultRegion = [...regions]
    .filter((region) => region.reviewSupplyChangeRate !== null && region.reviewSupplyChangeRate !== undefined)
    .sort((first, second) => first.reviewSupplyChangeRate - second.reviewSupplyChangeRate)[0] ?? regions[0];
  const activeSelectedRegion = searchParams.get("region") ?? defaultRegion?.region ?? null;
  const selectedRegionData = regions.find((region) => region.region === activeSelectedRegion) ?? null;

  function updateParams(updates) {
    const next = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === undefined || value === "") next.delete(key);
      else next.set(key, value);
    });
    setSearchParams(next, { replace: true });
  }

  const totals = useMemo(() => {
    const reviewers = regions.reduce((sum, item) => sum + item.reviewers, 0);
    const highRisk = regions.reduce((sum, item) => sum + item.highRisk, 0);

    return {
      reviewers,
      highRisk,
      highRiskRate: reviewers > 0 ? highRisk / reviewers : 0,
      crmTargets: regions.reduce((sum, item) => sum + item.crmTargets, 0),
    };
  }, [regions]);

  if (error) {
    return (
      <ErrorState message={error} />
    );
  }

  if (!regionalRisk) {
    return <Skeleton rows={5} columns={5} />;
  }

  return (
    <section className="pb-5">
      <WorkflowHeader
        eyebrow="REGIONAL OPERATIONS"
        title="콘텐츠 공급 권역 선택"
        description="음식점 리뷰 활동 지역을 기준으로 공급 둔화 권역을 찾고, 다음 단계에서 CRM 후보 리뷰어를 검토합니다."
        steps={["운영 신호 확인", "대상 선정", "근거 검토·판단", "운영안 설계", "실행·성과 추적"]}
        activeStep={1}
        aside={<div className="text-right"><DataModeBadge /><p className="mt-2 text-[11px] text-[#718078]">{regions.length}개 권역 · {totals.crmTargets.toLocaleString()}명 검토 대상</p></div>}
      />

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <SummaryMetric label="활동 리뷰어" value={`${totals.reviewers.toLocaleString()}명`} />
        <SummaryMetric label="고위험 리뷰어" value={`${totals.highRisk.toLocaleString()}명`} note={`${(totals.highRiskRate * 100).toFixed(1)}% · 운영 우선순위`} tone="warning" />
        <SummaryMetric label="CRM 검토 대상" value={`${totals.crmTargets.toLocaleString()}명`} tone="green" />
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex rounded-xl border border-[#DDE4DF] bg-white p-1">
          <button type="button" onClick={() => updateParams({ view: null })} className={`min-h-9 rounded-lg px-4 text-xs font-bold ${viewMode === "map" ? "bg-[#075C45] text-white" : "text-[#626D67]"}`}>권역 지도</button>
          <button type="button" onClick={() => updateParams({ view: "travel" })} className={`min-h-9 rounded-lg px-4 text-xs font-bold ${viewMode === "travel" ? "bg-[#075C45] text-white" : "text-[#626D67]"}`}>탐방 범위 분석</button>
        </div>
        {viewMode === "map" && (
          <div className="flex rounded-xl border border-[#DDE4DF] bg-white p-1">
            {[["supply", "리뷰 공급"], ["highRisk", "고위험"], ["newcomers", "신규 유입"]].map(([key, label]) => (
              <button key={key} type="button" onClick={() => setMapLayer(key)} className={`min-h-10 rounded-lg px-3 text-xs font-bold ${mapLayer === key ? "bg-[#E3F1EA] text-[#075C45]" : "text-[#718078]"}`}>{label}</button>
            ))}
          </div>
        )}
      </div>

      {viewMode === "travel" ? (
        <div className="mt-4"><RegionalTravelRange /></div>
      ) : (
        <>
          <div className="mt-4 grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
            <div>
              <RegionalBubbleMap
                regions={regions}
                hoveredRegion={hoveredRegion}
                onHoverRegion={setHoveredRegion}
                selectedRegion={activeSelectedRegion}
                onSelectRegion={(region) => updateParams({ region })}
                layer={mapLayer}
              />
              <p className="mt-3 rounded-xl bg-[#E9F1F3] px-4 py-3 text-xs leading-5 text-[#356A78]">
                권역은 {regionalRisk.comparisonYear}~{regionalRisk.selectionYear}년 음식점 리뷰 활동의 대표 지역(state)입니다. 거주지·직장·실제 생활 반경을 추론하지 않습니다.
              </p>
            </div>
            <RegionalInsightPanel region={selectedRegionData} />
          </div>

          <section className="mt-5 rounded-2xl border border-[#DDE4DF] bg-white p-5">
            <div className="flex items-center justify-between gap-3"><div><p className="text-xs font-black tracking-[0.1em] text-[#137A5A]">REGION RANKING</p><h2 className="mt-1 text-base font-black">리뷰 공급 우선 확인 순위</h2></div><span className="text-[11px] text-[#718078]">핀과 목록은 동일한 권역을 선택합니다</span></div>
            <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
              {regions.slice(0, 4).map((region, index) => (
                <button key={region.region} type="button" onClick={() => updateParams({ region: region.region })} className={`rounded-xl border p-4 text-left transition ${activeSelectedRegion === region.region ? "border-[#075C45] bg-[#EEF7F2]" : "border-[#E2E7E3] hover:border-[#9FBCAE]"}`}>
                  <span className="text-[10px] font-black text-[#789086]">PRIORITY {index + 1}</span>
                  <strong className="mt-1 block text-sm">{region.region} · {region.topCity}</strong>
                  <span className={`mt-2 block text-lg font-black ${region.reviewSupplyChangeRate < 0 ? "text-[#C94734]" : "text-[#075C45]"}`}>{region.reviewSupplyChangeRate >= 0 ? "+" : ""}{(region.reviewSupplyChangeRate * 100).toFixed(1)}%</span>
                </button>
              ))}
            </div>
          </section>
        </>
      )}

      <footer className="mt-8 border-t border-[#DDE4DF] pt-4 text-xs leading-5 text-[#718078]">Reviewer Retention · {operationsSummary.dataModeLabel} data · 고위험 비율과 모델 점수는 운영 우선순위이며 확률이 아닙니다.</footer>
    </section>
  );
}

function SummaryMetric({ label, value, note, tone }) {
  return (
    <article className="rounded-xl border border-[#DDE4DF] bg-white px-5 py-4">
      <p className="text-xs font-semibold text-[#718078]">{label}</p>
      <p className={`mt-1 text-xl font-black ${tone === "warning" ? "text-[#C94734]" : tone === "green" ? "text-[#075C45]" : "text-[#17211D]"}`}>{value}</p>
      {note && <p className="mt-1 text-[11px] text-[#8A948F]">{note}</p>}
    </article>
  );
}

export default RegionalRiskPage;
