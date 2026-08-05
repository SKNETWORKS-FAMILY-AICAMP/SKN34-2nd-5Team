import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";

import SupplyOverviewMap from "../components/regional/SupplyOverviewMap";
import GlobalWorkflowStepper from "../components/workflow/GlobalWorkflowStepper";
import { useOperationsSummary } from "../context/operations-context";
import { loadCityOperatingContext } from "../data";

const LAYERS = [
  ["supply", "공급 변화"],
  ["core", "핵심 리뷰어"],
  ["newcomers", "신규 유입"],
];
const VALID_LAYERS = new Set(LAYERS.map(([key]) => key));
const VALID_SCOPES = new Set(["city", "region"]);
const RANK_FIELDS = {
  supply: "supplyRank",
  core: "coreReviewerRank",
  newcomers: "newcomerRank",
};
const RANK_LABELS = {
  supply: "공급 위험 순",
  core: "통합 대상 순",
  newcomers: "신규 유입 순",
};
const STATE_NAMES = {
  AB: "Alberta, Canada",
  AZ: "Arizona, United States",
  CA: "California, United States",
  DE: "Delaware, United States",
  FL: "Florida, United States",
  ID: "Idaho, United States",
  IL: "Illinois, United States",
  IN: "Indiana, United States",
  LA: "Louisiana, United States",
  MO: "Missouri, United States",
  NJ: "New Jersey, United States",
  NV: "Nevada, United States",
  PA: "Pennsylvania, United States",
  TN: "Tennessee, United States",
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

function direction(value) {
  if (value === null || value === undefined) return "unknown";
  if (value < -0.05) return "down";
  if (value > 0.05) return "up";
  return "stable";
}

function operatingStatus(value) {
  const status = direction(value);
  if (status === "down") return "감소";
  if (status === "up") return "증가";
  if (status === "stable") return "보합";
  return "비교 불가";
}

function supplyStatusText(value) {
  if (value === null || value === undefined) return "비교 불가";
  return `${signedPercent(value)} (${operatingStatus(value)})`;
}

function supplyPeriodNote(value) {
  return direction(value) === "stable"
    ? "2017 → 2018 · 보합 범위(-5%~+5%)"
    : `2017 → 2018 · ${operatingStatus(value)}`;
}

function insightFor(entity) {
  const supply = direction(entity.reviewSupplyChangeRate);
  const newcomers = direction(entity.newPowerReviewerChangeRate);
  if (supply === "down" && newcomers === "down") return {
    tone: "danger", icon: "↘", title: "공급과 신규 유입이 함께 약화된 복합 위험",
    description: "기존 리뷰 활동과 신규 핵심 리뷰어 유입이 동시에 감소했습니다.",
    action: entity.reviewerNetMigration < 0
      ? `공급 감소 중 일부는 핵심 리뷰어 ${Math.abs(entity.reviewerNetMigration).toLocaleString()}명의 순유출로 확인됩니다. 핵심 리뷰어 검토와 지역 활성화 캠페인을 함께 준비하세요.`
      : "핵심 리뷰어 검토와 지역 활성화 캠페인을 함께 준비하세요.",
  };
  if (supply === "down" && newcomers === "up") return {
    tone: "danger", icon: "↘", title: "신규 유입보다 기존 리뷰 활동이 약화",
    description: "신규 핵심 리뷰어는 증가했지만 전체 리뷰 공급은 감소했습니다.",
    action: "기존 핵심 리뷰어의 활동 변화와 장기 공백을 우선 확인하세요.",
  };
  if (supply === "up" && newcomers === "down") return {
    tone: "warning", icon: "!", title: "공급 성장이 기존 리뷰어에 의존",
    description: "리뷰 공급은 증가했지만 신규 핵심 리뷰어 유입은 감소했습니다.",
    action: "신규 리뷰어 확보 캠페인으로 성장 기반을 보완하세요.",
  };
  if (supply === "up" && newcomers === "up") return {
    tone: "positive", icon: "↗", title: "공급과 신규 유입이 함께 성장",
    description: "리뷰 공급과 신규 핵심 리뷰어 유입이 모두 증가했습니다.",
    action: "성공 패턴을 유사 도시와 인접 활동권으로 확장하세요.",
  };
  if (supply === "stable" && newcomers === "down") return {
    tone: "warning", icon: "!", title: "현재 공급은 유지되지만 선행 위험 존재",
    description: `리뷰 공급은 ${signedPercent(entity.reviewSupplyChangeRate)}로 보합 범위이며 신규 핵심 리뷰어 유입은 감소했습니다.`,
    action: "신규 유입 둔화가 공급 감소로 이어지는지 관찰하세요.",
  };
  if (supply === "stable" && newcomers === "up") return {
    tone: "positive", icon: "→", title: "신규 유입의 공급 전환을 관찰할 지역",
    description: `리뷰 공급은 ${signedPercent(entity.reviewSupplyChangeRate)}로 보합 범위이며 신규 핵심 리뷰어 유입은 증가했습니다.`,
    action: "신규 리뷰어의 30·60·90일 활동 전환을 확인하세요.",
  };
  if (newcomers === "unknown") return {
    tone: supply === "down" ? "danger" : "neutral", icon: supply === "down" ? "↘" : "→",
    title: supply === "down" ? "리뷰 공급 감소 원인 검토 필요" : "신규 유입 전년 비교 불가",
    description: `리뷰 공급은 ${supplyStatusText(entity.reviewSupplyChangeRate)}이며 신규 유입은 전년 기준이 부족합니다.`,
    action: supply === "down" ? "핵심 리뷰어와 음식점 활동 변화를 확인하세요." : "공급 상태를 중심으로 운영 우선순위를 판단하세요.",
  };
  return {
    tone: "neutral", icon: "→", title: "리뷰 공급과 신규 유입이 안정적",
    description: "두 지표 모두 전년 대비 큰 변화 없이 유지되고 있습니다.",
    action: "현재 운영을 유지하고 다음 관찰 시점의 변화를 확인하세요.",
  };
}

function operatingInsightFor(layer, entity, insight, scope) {
  const unit = scope === "region" ? "권역" : "도시";
  if (layer === "core") {
    if (entity.crmTargets > 0) return {
      tone: entity.crmTargets >= 20 ? "danger" : "warning",
      icon: "●",
      title: "핵심 리뷰어 우선 검토 필요",
      message: `공급 변화에 미치는 영향이 큰 ${unit} 핵심 리뷰어 ${entity.crmTargets.toLocaleString()}명부터 검토하세요.`,
    };
    return {
      tone: "neutral",
      icon: "→",
      title: "권역 범위 검토 필요",
      message: `현재 ${unit}에는 배정된 핵심 리뷰어가 없어 권역 범위로 검토 대상을 넓히는 것이 좋습니다.`,
    };
  }
  if (layer === "newcomers") {
    if (entity.newPowerReviewers > 0) return {
      tone: direction(entity.newPowerReviewerChangeRate) === "down" ? "warning" : "positive",
      icon: direction(entity.newPowerReviewerChangeRate) === "down" ? "!" : "★",
      title: "신규 유입 활동 관찰",
      message: `신규 유입 리뷰어 ${entity.newPowerReviewers.toLocaleString()}명의 초기 활동이 다음 기간에도 유지되는지 관찰하세요.`,
    };
    return {
      tone: "neutral",
      icon: "→",
      title: "권역 단위 신규 유입 확인 필요",
      message: `현재 ${unit}에는 신규 유입 대상이 없어 권역 단위로 확인 범위를 넓히는 것이 좋습니다.`,
    };
  }
  return {
    tone: insight.tone,
    icon: insight.icon,
    title: insight.title,
    message: insight.action,
  };
}

function rankValue(entity, layer) {
  if (layer === "core") return `${entity.crmTargets.toLocaleString()}명`;
  if (layer === "newcomers") return `${entity.newPowerReviewers.toLocaleString()}명`;
  return signedPercent(entity.reviewSupplyChangeRate);
}

function HomePage() {
  const summary = useOperationsSummary();
  const [searchParams, setSearchParams] = useSearchParams();
  const [cityData, setCityData] = useState({ status: "loading", context: null, error: null });
  const layerParam = searchParams.get("layer");
  const layer = VALID_LAYERS.has(layerParam) ? layerParam : "supply";
  const scopeParam = searchParams.get("scope");
  const scope = VALID_SCOPES.has(scopeParam) ? scopeParam : "city";
  const rankField = RANK_FIELDS[layer];

  useEffect(() => {
    let cancelled = false;
    loadCityOperatingContext()
      .then((context) => {
        if (!cancelled) setCityData({ status: "ready", context, error: null });
      })
      .catch((error) => {
        if (!cancelled) setCityData({ status: "error", context: null, error: error.message });
      });
    return () => { cancelled = true; };
  }, []);

  const cities = useMemo(() => cityData.context?.cities ?? [], [cityData.context]);
  const regions = useMemo(() => cityData.context?.regions ?? [], [cityData.context]);
  const eligibleCities = useMemo(
    () => cities.filter((city) => city.minimumSampleMet && city[rankField] !== null),
    [cities, rankField],
  );
  const rankedCities = useMemo(
    () => [...eligibleCities].sort((first, second) => first[rankField] - second[rankField]),
    [eligibleCities, rankField],
  );
  const rankedRegions = useMemo(
    () => [...regions].filter((region) => region[rankField] !== null).sort((first, second) => first[rankField] - second[rankField]),
    [rankField, regions],
  );
  const defaultCity = rankedCities[0] ?? cities[0] ?? null;
  const defaultRegion = regions.find((region) => region.region === defaultCity?.state) ?? regions[0] ?? null;
  const selectedRegion = useMemo(() => {
    const regionCode = searchParams.get("region");
    return regions.find((region) => region.region === regionCode) ?? defaultRegion;
  }, [defaultRegion, regions, searchParams]);
  const selectedCity = useMemo(() => {
    const cityKey = searchParams.get("city");
    const requested = cities.find((city) => city.state === selectedRegion?.region && city.cityKey === cityKey);
    if (requested) return requested;
    return rankedCities.find((city) => city.state === selectedRegion?.region) ?? defaultCity;
  }, [cities, defaultCity, rankedCities, searchParams, selectedRegion]);

  const updateParams = (updates, replace = false) => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value === undefined || value === "") next.delete(key);
      else next.set(key, value);
    }
    setSearchParams(next, { replace });
  };

  useEffect(() => {
    if (!selectedCity || !selectedRegion) return;
    const next = new URLSearchParams(searchParams);
    next.set("region", selectedRegion.region);
    next.set("layer", layer);
    next.set("scope", scope);
    if (scope === "city") next.set("city", selectedCity.cityKey);
    else next.delete("city");
    if (next.toString() !== searchParams.toString()) setSearchParams(next, { replace: true });
  }, [layer, scope, searchParams, selectedCity, selectedRegion, setSearchParams]);

  const selectedEntity = scope === "region" ? selectedRegion : selectedCity;
  const rankedEntities = scope === "region" ? rankedRegions : rankedCities;
  const rankPosition = selectedEntity?.[rankField] ?? null;
  const selectCity = (city) => updateParams({ region: city.state, city: city.cityKey, scope: "city" });
  const selectRegion = (region) => {
    if (region) updateParams({ region: region.region, city: null, scope: "region" });
  };
  const setScope = (nextScope) => updateParams({
    scope: nextScope,
    city: nextScope === "city" ? selectedCity?.cityKey : null,
  });
  const moveRank = (offset) => {
    if (!rankPosition) return;
    const target = rankedEntities[rankPosition - 1 + offset];
    if (!target) return;
    if (scope === "region") selectRegion(target);
    else selectCity(target);
  };
  const selectFirstRank = () => {
    const target = rankedEntities[0];
    if (!target) return;
    if (scope === "region") selectRegion(target);
    else selectCity(target);
  };
  const setLayer = (nextLayer) => updateParams({ layer: nextLayer });

  const regionCitiesRanked = useMemo(
    () => rankedCities.filter((city) => city.state === selectedRegion?.region),
    [rankedCities, selectedRegion],
  );
  const comparisonCities = useMemo(() => {
    if (scope === "region") return regionCitiesRanked.slice(0, 4);
    const index = regionCitiesRanked.findIndex((city) => city.cityKey === selectedCity?.cityKey);
    const start = Math.max(0, Math.min(index - 1, regionCitiesRanked.length - 4));
    return regionCitiesRanked.slice(start, start + 4);
  }, [regionCitiesRanked, scope, selectedCity]);

  const insight = selectedEntity ? insightFor(selectedEntity) : null;
  const operatingInsight = selectedEntity && insight ? operatingInsightFor(layer, selectedEntity, insight, scope) : null;
  const locationQuery = selectedRegion
    ? `region=${encodeURIComponent(selectedRegion.region)}${scope === "city" && selectedCity ? `&city=${encodeURIComponent(selectedCity.cityKey)}` : ""}`
    : "";
  const reviewerScope = layer === "core" ? "core" : layer === "newcomers" ? "newcomers" : "region";
  const queueTarget = `/reviewers?${locationQuery}&mode=individual&scope=${reviewerScope}&status=미검토&sort=우선순위`;
  const campaignTarget = `/playbook?mode=region&${locationQuery}`;
  const panel = selectedEntity && insight
    ? panelFor(layer, selectedEntity, insight, queueTarget, campaignTarget, scope)
    : null;
  const workflowSteps = [
    { label: "운영 신호 확인" },
    { label: "대상 선정", href: panel?.href ?? null },
    { label: "근거 검토·판단" },
    { label: "운영안 설계" },
    { label: "실행·성과 추적" },
  ];

  return (
    <section className="pb-3">
      <div className="mb-3">
        <GlobalWorkflowStepper steps={workflowSteps} currentStep={1} />
      </div>
      <div className="home-command-grid">
        <section className="console-card min-w-0 overflow-hidden p-3">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3 px-1">
            <div className="flex rounded-lg border border-[#DDE4DF] bg-[#F7F9F7] p-1" aria-label="지도 지표 선택">
              {LAYERS.map(([key, label]) => <button key={key} type="button" title={`${RANK_LABELS[key]} 기준`} onClick={() => setLayer(key)} className={`min-h-9 rounded-md px-4 text-xs font-bold transition ${layer === key ? "bg-[#075C45] text-white shadow-sm" : "text-[#526159] hover:bg-white"}`}>{label}</button>)}
            </div>
            <span className="text-[10px] text-[#718078]">{RANK_LABELS[layer]} · 음식점 소재지 기준 · 거주지 아님</span>
          </div>
          {cityData.status === "loading" && <div className="h-[430px] animate-pulse rounded-xl bg-[#EDF1EE]" aria-label="도시 데이터를 불러오는 중" />}
          {cityData.status === "error" && <div className="grid h-[430px] place-items-center rounded-xl bg-[#FAF4F2] px-6 text-center"><div><strong className="block text-sm text-[#B4402F]">도시 운영 데이터를 불러오지 못했습니다.</strong><span className="mt-2 block text-xs text-[#718078]">{cityData.error}</span></div></div>}
          {cityData.status === "ready" && (!cityData.context?.available || cities.length === 0) && <div className="grid h-[430px] place-items-center rounded-xl bg-[#F4F6F3] text-sm text-[#718078]">표시할 도시 데이터가 없습니다.</div>}
          {cityData.status === "ready" && selectedCity && selectedRegion && (
            <SupplyOverviewMap
              cities={cities}
              regions={regions}
              layer={layer}
              scope={scope}
              selectedRegion={selectedRegion}
              selectedCity={selectedCity}
              rankPosition={rankPosition}
              rankTotal={rankedEntities.length}
              onSelectRegion={selectRegion}
              onSelectCity={selectCity}
              onSetScope={setScope}
              onRankOffset={moveRank}
              onFirstRank={selectFirstRank}
            />
          )}
        </section>

        <aside className="console-card flex min-h-[486px] flex-col overflow-hidden">
          {selectedEntity && panel ? (
            <>
              <div className="border-b border-[#E5E9E6] px-4 py-3.5">
                <div className="flex min-w-0 items-start gap-2.5"><LocationGlyph /><div className="min-w-0"><div className="flex items-center gap-2"><h2 className="truncate text-xl font-black">{scope === "region" ? `${selectedRegion.region} · ${STATE_NAMES[selectedRegion.region]?.split(",")[0] ?? selectedRegion.region}` : `${selectedCity.state} · ${displayCity(selectedCity.city)}`}</h2><span className="rounded border border-[#9CCDB8] bg-[#ECF7F2] px-1.5 py-0.5 text-[9px] font-bold text-[#075C45]">{scope === "region" ? "권역 요약" : "도시 상세"}</span></div><p className="mt-0.5 text-[11px] text-[#718078]">{scope === "region" ? `${STATE_NAMES[selectedRegion.region] ?? selectedRegion.region} · 표본 충족 도시 ${selectedRegion.eligibleCityCount}/${selectedRegion.cityCount}곳` : `${STATE_NAMES[selectedCity.state] ?? selectedCity.state} · 활동 반경 ${selectedCity.displayRadiusKm.toFixed(0)}km`}</p></div></div>
              </div>
              <div className={`mx-4 mt-3 rounded-lg border px-3 py-2.5 ${panel.danger ? "border-[#F1C0B6] bg-[#FFF6F3]" : panel.warning ? "border-[#E9D3A8] bg-[#FFF9EC]" : "border-[#BFDBCE] bg-[#F2F8F5]"}`}>
                <div className="flex items-start gap-2.5"><TrendGlyph danger={panel.danger} /><div><p className={`text-xs font-black ${panel.danger ? "text-[#B4402F]" : panel.warning ? "text-[#8C620F]" : "text-[#075C45]"}`}>{panel.alert}</p><p className="mt-1 text-[10px] text-[#6E7973]">{panel.alertNote}</p></div></div>
              </div>
              <div className="mt-2 divide-y divide-[#E7EBE8] border-y border-[#E7EBE8]">
                {panel.metrics.map((metric) => <MetricRow key={metric.label} {...metric} />)}
              </div>
              <div className="mt-auto px-4 py-3">
                {panel.disabled ? <button type="button" disabled title={panel.disabledNote} className="flex min-h-11 w-full cursor-not-allowed items-center justify-center gap-3 rounded-lg bg-[#E7ECE9] px-4 text-xs font-black text-[#8A958F]">{panel.cta}</button> : <Link to={panel.href} className="flex min-h-11 items-center justify-center gap-3 rounded-lg bg-[#087454] px-4 text-xs font-black text-white shadow-[0_5px_14px_rgba(7,92,69,0.15)] hover:bg-[#064936]">{panel.cta}<span className="text-lg leading-none">→</span></Link>}
                {panel.secondaryHref && <Link to={panel.secondaryHref} className="mt-2 flex min-h-10 items-center justify-center gap-2 rounded-lg border border-[#9CCDB8] bg-white px-4 text-[11px] font-black text-[#075C45] hover:bg-[#F1F8F4]">{panel.secondaryCta}<span>→</span></Link>}
                {panel.disabledNote && <p className="mt-2 rounded-md border border-[#E1E6E3] bg-[#FAFBFA] px-2.5 py-2 text-[9px] leading-4 text-[#718078]">{panel.disabledNote}</p>}
                <p className="mt-2 rounded-md bg-[#F6F7F5] px-2.5 py-2 text-[9px] leading-4 text-[#718078]">ⓘ 2017→2018 공개 음식점 리뷰 활동입니다. 위치 표시는 거주지를 의미하지 않습니다.</p>
              </div>
            </>
          ) : <div className="grid flex-1 place-items-center p-6 text-sm text-[#718078]">권역 또는 리뷰 활동 도시를 선택하세요.</div>}
        </aside>
      </div>

      {selectedEntity && insight && operatingInsight && (
        <section className="console-card mt-3 overflow-hidden px-4 py-3">
          <h2 className="text-sm font-black">{scope === "region" ? "권역" : "도시"} 운영 진단 · {operatingInsight.title}</h2>
          <div className="home-diagnostics-grid mt-3 divide-y divide-[#E5E9E6] xl:divide-x xl:divide-y-0">
            <div className="py-2 pr-4"><p className="text-[10px] font-bold text-[#718078]">{scope === "region" ? "권역" : "도시"} {RANK_LABELS[layer]}</p><p className="mt-2 text-3xl font-black text-[#E15F48]">{rankPosition ?? "—"}<span className="ml-1 text-base font-medium text-[#526159]">/ {rankedEntities.length}</span></p><p className="mt-2 text-[10px] leading-4 text-[#718078]">현재 탭 운영 기준</p></div>
            <div className="px-0 py-3 xl:px-5 xl:py-2"><p className="text-[10px] font-bold text-[#526159]">리뷰 공급 2017 → 2018</p><SupplyBars entity={selectedEntity} /></div>
            <div className="px-0 py-3 xl:px-5 xl:py-2">
              <p className="text-[10px] font-bold text-[#526159]">{selectedRegion.region} 권역 내 도시 순위</p>
              <div className="mt-2 text-[10px]"><div className="grid border-b border-[#E5E9E6] pb-1 text-[#849089]" style={{ gridTemplateColumns: "minmax(0, 1fr) 42px 78px" }}><span>도시</span><span className="text-right">순위</span><span className="text-right">{RANK_LABELS[layer]}</span></div>{comparisonCities.map((city) => <button key={`${city.state}-${city.cityKey}`} type="button" onClick={() => selectCity(city)} className={`grid min-h-6 w-full items-center rounded px-1 text-left ${scope === "city" && city.cityKey === selectedCity.cityKey ? "bg-[#DFF1E8] font-black text-[#075C45]" : "hover:bg-[#F4F7F5]"}`} style={{ gridTemplateColumns: "minmax(0, 1fr) 42px 78px" }}><span className="truncate">{displayCity(city.city)}</span><span className="text-right">{city[rankField]}</span><span className="text-right">{rankValue(city, layer)}</span></button>)}</div>
            </div>
            <div className="px-0 py-3 xl:pl-5 xl:py-2">
              <div className={`flex h-full min-h-[108px] flex-col justify-center rounded-xl border px-4 py-3 ${operatingInsight.tone === "danger" ? "border-[#F0BDB2] bg-[#FFF3EF]" : operatingInsight.tone === "warning" || operatingInsight.tone === "neutral" ? "border-[#E7D4AE] bg-[#FFF9EC]" : "border-[#B9DCCB] bg-[#EFF8F3]"}`}>
                <p className={`text-xs font-black ${operatingInsight.tone === "danger" ? "text-[#B4402F]" : operatingInsight.tone === "warning" || operatingInsight.tone === "neutral" ? "text-[#8C620F]" : "text-[#075C45]"}`}>핵심 인사이트</p>
                <p className="mt-2 flex gap-2 text-sm font-bold leading-6 text-[#26332D]"><span className={`shrink-0 ${operatingInsight.tone === "danger" ? "text-[#E15F48]" : operatingInsight.tone === "warning" || operatingInsight.tone === "neutral" ? "text-[#B8821C]" : "text-[#087454]"}`}>{operatingInsight.icon}</span><span>{operatingInsight.message}</span></p>
              </div>
            </div>
          </div>
        </section>
      )}

      <footer className="mt-3 flex flex-col gap-1 border-t border-[#DDE4DF] pt-2 text-[9px] leading-4 text-[#718078] sm:flex-row sm:justify-between"><p>Reviewer Retention · PROJECT data · 모델 점수는 확률이 아닌 운영 우선순위입니다.</p><p>© 2026 SKN34-2nd-5Team · Yelp Open Dataset 기반 비상업 분석 · Yelp 공식 서비스가 아닙니다.</p><span className="sr-only">전체 코호트 {summary.totalReviewers.toLocaleString()}명 · CRM 검토 대상 {summary.targetUsers.toLocaleString()}명</span></footer>
    </section>
  );
}

function panelFor(layer, entity, insight, queueHref, campaignHref, scope) {
  const unit = scope === "region" ? "권역" : "도시";
  if (layer === "core") return {
    danger: entity.crmTargets >= 20,
    warning: entity.crmTargets > 0 && entity.crmTargets < 20,
    alert: entity.crmTargets > 0 ? `핵심 리뷰어 검토 대상이 배정된 ${unit}입니다.` : `현재 배정된 CRM 검토 대상이 없는 ${unit}입니다.`,
    alertNote: `${scope === "region" ? "권역" : "주 활동 도시"} 기준 · 통합 검토 대상 ${entity.crmTargets.toLocaleString()}명`,
    metrics: [
      { type: "target", label: "통합 검토 대상", note: `${unit} 운영 배정`, value: `${entity.crmTargets.toLocaleString()}명`, danger: entity.crmTargets >= 20 },
      { type: "reviewer", label: "활동 리뷰어", note: "2018년 고유 음식점 리뷰어", value: `${entity.activeReviewers.toLocaleString()}명` },
      scope === "region"
        ? { type: "business", label: "표본 충족 도시", note: `${entity.cityCount.toLocaleString()}개 도시 중`, value: `${entity.eligibleCityCount.toLocaleString()}곳` }
        : { type: "business", label: "활동 음식점", note: "2018년 공개 리뷰 기준", value: `${entity.activeBusinesses.toLocaleString()}곳` },
      { type: "trend", label: "리뷰 공급 변화", note: supplyPeriodNote(entity.reviewSupplyChangeRate), value: signedPercent(entity.reviewSupplyChangeRate), danger: entity.reviewSupplyChangeRate < -0.05 },
    ], href: entity.crmTargets > 0 ? queueHref : null, cta: `관리 대상 ${entity.crmTargets.toLocaleString()}명 검토`, disabled: entity.crmTargets === 0, disabledNote: entity.crmTargets === 0 ? `현재 선택 ${unit}에는 핵심 리뷰어 관리 대상이 없습니다.` : null, secondaryHref: null, secondaryCta: null,
  };
  if (layer === "newcomers") return {
    danger: direction(entity.newPowerReviewerChangeRate) === "down",
    warning: direction(entity.newPowerReviewerChangeRate) === "unknown",
    alert: direction(entity.newPowerReviewerChangeRate) === "down" ? "신규 핵심 리뷰어 유입이 감소했습니다." : direction(entity.newPowerReviewerChangeRate) === "up" ? "신규 핵심 리뷰어 유입이 증가했습니다." : "신규 핵심 리뷰어 유입을 관찰하세요.",
    alertNote: `2017 ${entity.previousYearNewPowerReviewers.toLocaleString()}명 → 2018 ${entity.newPowerReviewers.toLocaleString()}명`,
    metrics: [
      { type: "star", label: "신규 핵심 리뷰어", note: "2018년 최초 코호트 진입", value: `${entity.newPowerReviewers.toLocaleString()}명` },
      { type: "trend", label: "신규 유입 변화", note: "2017 → 2018", value: signedPercent(entity.newPowerReviewerChangeRate), danger: direction(entity.newPowerReviewerChangeRate) === "down" },
      { type: "reviewer", label: "활동 리뷰어", note: "2018년 고유 음식점 리뷰어", value: `${entity.activeReviewers.toLocaleString()}명` },
      scope === "region"
        ? { type: "business", label: "표본 충족 도시", note: `${entity.cityCount.toLocaleString()}개 도시 중`, value: `${entity.eligibleCityCount.toLocaleString()}곳` }
        : { type: "business", label: "활동 음식점", note: "공개 리뷰 활동 기준", value: `${entity.activeBusinesses.toLocaleString()}곳` },
    ], href: entity.newPowerReviewers > 0 ? queueHref : null, cta: `신규 핵심 리뷰어 ${entity.newPowerReviewers.toLocaleString()}명 확인`, disabled: entity.newPowerReviewers === 0, disabledNote: entity.newPowerReviewers === 0 ? `현재 선택 ${unit}에는 신규 핵심 리뷰어가 없습니다.` : null, secondaryHref: null, secondaryCta: null,
  };
  return {
    danger: insight.tone === "danger",
    warning: insight.tone === "warning",
    alert: insight.title,
    alertNote: `리뷰 공급 ${supplyStatusText(entity.reviewSupplyChangeRate)} · 신규 유입 ${signedPercent(entity.newPowerReviewerChangeRate)}`,
    metrics: [
      { type: "trend", label: "리뷰 공급 변화", note: supplyPeriodNote(entity.reviewSupplyChangeRate), value: signedPercent(entity.reviewSupplyChangeRate), danger: entity.reviewSupplyChangeRate < -0.05 },
      { type: "reviewer", label: "핵심 리뷰어 순유출입", note: `2017 → 2018 · 유출 ${entity.reviewerOutflowCount.toLocaleString()}명 · 유입 ${entity.reviewerInflowCount.toLocaleString()}명`, value: `${entity.reviewerNetMigration >= 0 ? "+" : ""}${entity.reviewerNetMigration.toLocaleString()}명`, danger: entity.reviewerNetMigration < 0 },
      {
        type: "reviewer",
        label: "활동 리뷰어",
        note: (
          <>
            <span className="block">2018년 고유 음식점 리뷰어</span>
            <span className="mt-0.5 block">
              이 중 핵심 리뷰어 <strong className="font-black text-[#087454]">{(entity.coreReviewers ?? 0).toLocaleString()}명</strong>
            </span>
          </>
        ),
        value: `${entity.activeReviewers.toLocaleString()}명`,
      },
      { type: "target", label: "통합 검토 대상", note: `${unit} 기준`, value: `${entity.crmTargets.toLocaleString()}명` },
      { type: "star", label: "신규 핵심 리뷰어", note: "2018년 유입", value: `${entity.newPowerReviewers.toLocaleString()}명` },
    ], href: (entity.coreReviewers ?? 0) > 0 ? queueHref : null, cta: `핵심 리뷰어 ${(entity.coreReviewers ?? 0).toLocaleString()}명 확인`, disabled: (entity.coreReviewers ?? 0) === 0, disabledNote: (entity.coreReviewers ?? 0) === 0 ? `현재 선택 ${unit}에는 핵심 리뷰어가 없습니다.` : null, secondaryHref: campaignHref, secondaryCta: `${unit} 활성화 캠페인 설계`,
  };
}

function MetricRow({ type, label, note, value, danger = false }) {
  return <div className="grid min-h-12 grid-cols-[32px_1fr_auto] items-center gap-2 px-4 py-2"><MetricGlyph type={type} danger={danger} /><div><p className="text-[11px] font-bold text-[#26332D]">{label}</p><p className="mt-0.5 text-[9px] text-[#849089]">{note}</p></div><strong className={`text-xl ${danger ? "text-[#E1513A]" : "text-[#087454]"}`}>{value}</strong></div>;
}

function MetricGlyph({ type, danger }) {
  const color = danger ? "#E1513A" : "#087454";
  if (type === "star") return <svg viewBox="0 0 24 24" className="h-6 w-6" fill="#C49518" aria-hidden="true"><path d="m12 2.8 2.8 5.7 6.3.9-4.6 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L2.9 9.4l6.3-.9L12 2.8Z" /></svg>;
  if (type === "reviewer") return <svg viewBox="0 0 24 24" className="h-6 w-6" fill={color} aria-hidden="true"><circle cx="12" cy="7" r="4" /><path d="M4 21c.5-5 3.2-7.5 8-7.5S19.5 16 20 21H4Z" /></svg>;
  if (type === "target") return <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke={color} strokeWidth="2" aria-hidden="true"><circle cx="9" cy="7" r="3" fill={color} /><path d="M3 19c.5-4 2.5-6 6-6 2 0 3.5.6 4.5 1.7M15 17l2 2 4-5" /></svg>;
  if (type === "business") return <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke={color} strokeWidth="2" aria-hidden="true"><path d="M4 10h16M5 10v10h14V10M3 10l2-6h14l2 6M9 20v-5h6v5" /></svg>;
  return <TrendGlyph danger={danger} />;
}

function TrendGlyph({ danger }) {
  return <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke={danger ? "#E1513A" : "#087454"} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={danger ? "m3 6 6 6 4-4 8 8M16 16h5v-5" : "m3 17 6-6 4 4 8-8M16 7h5v5"} /></svg>;
}

function LocationGlyph() {
  return <svg viewBox="0 0 24 24" className="h-8 w-8 shrink-0" fill="#2F9A78" aria-hidden="true"><path d="M12 2a7 7 0 0 0-7 7c0 5.1 7 13 7 13s7-7.9 7-13a7 7 0 0 0-7-7Zm0 10a3 3 0 1 1 0-6 3 3 0 0 1 0 6Z" /></svg>;
}

function SupplyBars({ entity }) {
  const previous = entity.previousYearReviewCount ?? 0;
  const current = entity.reviewCount ?? 0;
  const maximum = Math.max(previous, current, 1);
  return <div className="mt-2 grid grid-cols-2 gap-4"><Bar year="2017" value={previous} height={Math.max(8, Math.round((previous / maximum) * 52))} tone="bg-[#AFC9BB]" /><Bar year="2018" value={current} height={Math.max(8, Math.round((current / maximum) * 52))} tone={current < previous ? "bg-[#E36F58]" : "bg-[#087454]"} /></div>;
}

function Bar({ year, value, height, tone }) {
  return <div className="grid grid-cols-[34px_1fr] items-end gap-2"><div><p className="text-[9px] text-[#849089]">{year}</p><p className="text-[10px] font-black">{value.toLocaleString()}</p></div><div className="flex h-14 items-end rounded bg-[#F1F3F1] px-1"><span className={`block w-full rounded-sm ${tone}`} style={{ height }} /></div></div>;
}

export default HomePage;
