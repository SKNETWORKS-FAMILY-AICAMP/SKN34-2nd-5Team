import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";

import EmptyState from "../components/common/EmptyState";
import ReviewerFilters from "../components/reviewers/ReviewerFilters";
import ReviewerSplitList from "../components/reviewers/ReviewerSplitList";
import ReviewerSplitPanel from "../components/reviewers/ReviewerSplitPanel";
import GlobalWorkflowStepper from "../components/workflow/GlobalWorkflowStepper";
import { useOperationsSummary, useReviewers, useRiskTypes } from "../context/operations-context";
import { useDecisions } from "../context/DecisionContext";

const PAGE_SIZE = 10;
const VALID_STATUS = ["전체", "미검토", "검토 완료"];
const VALID_SCOPE = ["region", "core", "newcomers"];
const VALID_SORT = ["우선순위", "중단 점수", "약화 점수", "활동 감소순", "리뷰 공백"];
const VALID_CRM = ["전체", "상위 20%", "상위 20% 제외"];
const SCOPE_LABELS = { region: "권역 종합", core: "핵심 리뷰어", newcomers: "신규 유입" };

function normalize(value) { return String(value ?? "").trim().toLocaleLowerCase(); }
function readEnum(params, key, fallback, values) { const value = params.get(key); return value !== null && values.includes(value) ? value : fallback; }

function ReviewerListPage() {
  const summary = useOperationsSummary();
  const reviewers = useReviewers();
  const riskTypes = useRiskTypes();
  const { decisions } = useDecisions();
  const [searchParams, setSearchParams] = useSearchParams();
  const regionalCampaignMode = searchParams.get("mode") === "region";
  const scopeFilter = readEnum(searchParams, "scope", regionalCampaignMode ? "region" : "core", VALID_SCOPE);
  const regionFilter = searchParams.get("region") ?? "전체";
  const cityFilter = searchParams.get("city") ?? "전체";
  const searchText = searchParams.get("q") ?? "";
  const statusFilter = readEnum(searchParams, "status", regionalCampaignMode ? "전체" : "미검토", VALID_STATUS);
  const riskTypeFilter = searchParams.get("riskType") ?? "전체";
  const sortRule = readEnum(searchParams, "sort", "우선순위", VALID_SORT);
  const modelJudgmentFilter = searchParams.get("judgment") ?? "전체";
  const crmRangeFilter = readEnum(searchParams, "crm", "전체", VALID_CRM);
  const recencyFilter = searchParams.get("recency") ?? "전체";
  const activeMonthsFilter = searchParams.get("activeMonths") ?? "전체";
  const atlasRecencyMin = searchParams.has("recencyMin") ? Number(searchParams.get("recencyMin")) : null;
  const atlasRecencyMaxRaw = searchParams.get("recencyMax");
  const atlasRecencyMax = atlasRecencyMaxRaw === "" || atlasRecencyMaxRaw === null ? Infinity : Number(atlasRecencyMaxRaw);
  const requestedPage = Math.max(1, Number.parseInt(searchParams.get("page") ?? "1", 10) || 1);
  const [activeReviewerId, setActiveReviewerId] = useState(null);
  const [selectedIds, setSelectedIds] = useState(() => new Set());

  const reviewersWithDecisions = useMemo(() => reviewers.map((reviewer) => ({ ...reviewer, managerDecision: decisions[reviewer.userId]?.decision ?? null })), [decisions, reviewers]);
  const regionOptions = useMemo(() => [...new Set(reviewersWithDecisions.map((reviewer) => reviewer.region).filter(Boolean))].sort(), [reviewersWithDecisions]);
  const cityOptions = useMemo(() => {
    const options = new Set(reviewersWithDecisions.filter((reviewer) => regionFilter === "전체" || reviewer.region === regionFilter).map((reviewer) => reviewer.topCity).filter(Boolean));
    if (cityFilter !== "전체") options.add(cityFilter);
    return [...options].sort((a, b) => a.localeCompare(b));
  }, [cityFilter, regionFilter, reviewersWithDecisions]);

  const scopedReviewers = useMemo(() => reviewersWithDecisions.filter((reviewer) => {
    if (scopeFilter === "core" && !reviewer.crmTarget) return false;
    if (scopeFilter === "newcomers" && !reviewer.isNewcomer) return false;
    if (regionFilter !== "전체" && reviewer.region !== regionFilter) return false;
    if (cityFilter !== "전체" && normalize(reviewer.topCity) !== normalize(cityFilter)) return false;
    return true;
  }), [cityFilter, regionFilter, reviewersWithDecisions, scopeFilter]);

  const completedCount = scopedReviewers.filter((reviewer) => reviewer.managerDecision).length;
  const pendingCount = scopedReviewers.length - completedCount;
  const filteredReviewers = useMemo(() => {
    let result = [...scopedReviewers];
    if (searchText.trim()) { const query = normalize(searchText); result = result.filter((reviewer) => normalize(reviewer.userId).includes(query)); }
    if (statusFilter === "미검토") result = result.filter((reviewer) => !reviewer.managerDecision);
    if (statusFilter === "검토 완료") result = result.filter((reviewer) => reviewer.managerDecision);
    if (riskTypeFilter !== "전체") result = result.filter((reviewer) => reviewer.riskType === riskTypeFilter);
    if (modelJudgmentFilter !== "전체") result = result.filter((reviewer) => reviewer.modelJudgment === modelJudgmentFilter);
    if (crmRangeFilter === "상위 20%") result = result.filter((reviewer) => reviewer.crmTarget);
    if (crmRangeFilter === "상위 20% 제외") result = result.filter((reviewer) => !reviewer.crmTarget);
    if (recencyFilter !== "전체") {
      const [minimum, maximum] = recencyFilter === "180+" ? [180, Infinity] : recencyFilter.split("-").map(Number);
      result = result.filter((reviewer) => reviewer.recentRecencyDays >= minimum && reviewer.recentRecencyDays < maximum);
    }
    if (atlasRecencyMin !== null) result = result.filter((reviewer) => reviewer.recentRecencyDays >= atlasRecencyMin && reviewer.recentRecencyDays < atlasRecencyMax);
    if (activeMonthsFilter !== "전체") result = result.filter((reviewer) => reviewer.recentActiveMonths === Number(activeMonthsFilter));
    if (sortRule === "중단 점수") result.sort((a, b) => b.scores.stopped - a.scores.stopped);
    else if (sortRule === "약화 점수") result.sort((a, b) => b.scores.weakened - a.scores.weakened);
    else if (sortRule === "활동 감소순") result.sort((a, b) => b.activeMonthDeclineRate - a.activeMonthDeclineRate);
    else if (sortRule === "리뷰 공백") result.sort((a, b) => b.recentRecencyDays - a.recentRecencyDays);
    else result.sort((a, b) => a.priorityRank - b.priorityRank);
    return result;
  }, [activeMonthsFilter, atlasRecencyMax, atlasRecencyMin, crmRangeFilter, modelJudgmentFilter, recencyFilter, riskTypeFilter, scopedReviewers, searchText, sortRule, statusFilter]);

  const pageCount = Math.max(1, Math.ceil(filteredReviewers.length / PAGE_SIZE));
  const page = Math.min(requestedPage, pageCount);
  const pageStart = (page - 1) * PAGE_SIZE;
  const visibleReviewers = filteredReviewers.slice(pageStart, pageStart + PAGE_SIZE);
  const activeReviewer = visibleReviewers.find((reviewer) => reviewer.userId === activeReviewerId) ?? visibleReviewers[0] ?? null;

  const setFilter = useCallback((key, value, fallback = "전체") => {
    setSearchParams((previous) => { const next = new URLSearchParams(previous); if (value === fallback || value === "") next.delete(key); else next.set(key, value); next.delete("page"); return next; }, { replace: true });
  }, [setSearchParams]);
  const setRegion = (value) => setSearchParams((previous) => { const next = new URLSearchParams(previous); if (value === "전체") next.delete("region"); else next.set("region", value); next.delete("city"); next.delete("page"); return next; }, { replace: true });
  const setPage = (value) => setSearchParams((previous) => { const next = new URLSearchParams(previous); if (value <= 1) next.delete("page"); else next.set("page", String(value)); return next; }, { replace: true });
  const resetFilters = () => setSearchParams(new URLSearchParams({ mode: regionalCampaignMode ? "region" : "individual", scope: scopeFilter }), { replace: true });
  const clearAtlas = () => setSearchParams((previous) => { const next = new URLSearchParams(previous); ["recencyMin", "recencyMax", "page"].forEach((key) => next.delete(key)); return next; }, { replace: true });
  const toggleSelect = (userId) => setSelectedIds((previous) => { const next = new Set(previous); if (next.has(userId)) next.delete(userId); else next.add(userId); return next; });
  const toggleSelectAll = (ids) => setSelectedIds((previous) => ids.every((id) => previous.has(id)) ? new Set() : new Set(ids));

  useEffect(() => {
    function onKeyDown(event) { const tag = document.activeElement?.tagName; if (["INPUT", "TEXTAREA", "SELECT"].includes(tag) || !["j", "k"].includes(event.key)) return; const index = visibleReviewers.findIndex((reviewer) => reviewer.userId === activeReviewer?.userId); const nextIndex = event.key === "j" ? Math.min(index + 1, visibleReviewers.length - 1) : Math.max(index - 1, 0); if (visibleReviewers[nextIndex]) setActiveReviewerId(visibleReviewers[nextIndex].userId); }
    window.addEventListener("keydown", onKeyDown); return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeReviewer?.userId, visibleReviewers]);

  const selectedReviewers = filteredReviewers.filter((reviewer) => selectedIds.has(reviewer.userId));
  const campaignParams = new URLSearchParams({ mode: "region" });
  if (regionFilter !== "전체") campaignParams.set("region", regionFilter);
  if (cityFilter !== "전체") campaignParams.set("city", cityFilter);
  if (selectedReviewers.length) campaignParams.set("members", selectedReviewers.map((reviewer) => reviewer.userId).join(","));
  const campaignHref = `/playbook?${campaignParams.toString()}`;
  const homeParams = new URLSearchParams({
    layer: scopeFilter === "newcomers" ? "newcomers" : scopeFilter === "core" ? "core" : "supply",
    scope: cityFilter !== "전체" ? "city" : "region",
  });
  if (regionFilter !== "전체") homeParams.set("region", regionFilter);
  if (cityFilter !== "전체") homeParams.set("city", cityFilter);
  const homeHref = `/?${homeParams.toString()}`;
  const detailParams = new URLSearchParams({ source: scopeFilter });
  if (regionFilter !== "전체") detailParams.set("region", regionFilter);
  if (cityFilter !== "전체") detailParams.set("city", cityFilter);
  const evidenceHref = activeReviewer
    ? `/reviewers/${encodeURIComponent(activeReviewer.userId)}?${detailParams.toString()}`
    : null;
  const planHref = regionalCampaignMode
    ? selectedReviewers.length > 0 ? campaignHref : null
    : activeReviewer?.managerDecision
      ? `/playbook?mode=individual&reviewer=${encodeURIComponent(activeReviewer.userId)}`
      : null;
  const workflowSteps = [
    { label: "운영 신호 확인", href: homeHref },
    { label: "대상 선정" },
    { label: "근거 검토·판단", href: evidenceHref },
    { label: "운영안 설계", href: planHref },
    { label: "실행·성과 추적" },
  ];
  return (
    <section className="pb-20">
      <GlobalWorkflowStepper steps={workflowSteps} currentStep={2} />

      {atlasRecencyMin !== null && <div className="mt-2 flex items-center rounded-lg bg-[#EAF4EF] px-3 py-2 text-[11px] text-[#075C45]">Signal Atlas 공백 조건 적용 · {atlasRecencyMin}~{Number.isFinite(atlasRecencyMax) ? atlasRecencyMax : "∞"}일<button type="button" onClick={clearAtlas} className="ml-auto font-bold underline">조건 해제</button></div>}

      <div className="mt-3"><ReviewerFilters
        searchText={searchText} onSearchChange={(value) => setFilter("q", value, "")}
        scopeFilter={scopeFilter} onScopeChange={(value) => setFilter("scope", value, regionalCampaignMode ? "region" : "core")}
        regionFilter={regionFilter} onRegionChange={setRegion} regionOptions={regionOptions}
        cityFilter={cityFilter} onCityChange={(value) => setFilter("city", value)} cityOptions={cityOptions}
        statusFilter={statusFilter} onStatusChange={(value) => setFilter("status", value, regionalCampaignMode ? "전체" : "미검토")}
        riskTypeFilter={riskTypeFilter} onRiskTypeChange={(value) => setFilter("riskType", value)}
        sortRule={sortRule} onSortChange={(value) => setFilter("sort", value, "우선순위")} riskTypes={riskTypes}
        modelJudgmentFilter={modelJudgmentFilter} onModelJudgmentChange={(value) => setFilter("judgment", value)}
        crmRangeFilter={crmRangeFilter} onCrmRangeChange={(value) => setFilter("crm", value)}
        recencyFilter={recencyFilter} onRecencyChange={(value) => setFilter("recency", value)}
        activeMonthsFilter={activeMonthsFilter} onActiveMonthsChange={(value) => setFilter("activeMonths", value)}
        pendingCount={pendingCount} completedCount={completedCount} totalCount={scopedReviewers.length}
      /></div>

      {visibleReviewers.length === 0 ? <div className="mt-3"><EmptyState title="조건에 맞는 리뷰어가 없습니다" description="범위나 지역·상세 필터를 바꿔 보세요." actionLabel="필터 초기화" onAction={resetFilters} /></div> : (
        <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1.8fr)_minmax(350px,0.85fr)] xl:items-start">
          <div className="min-w-0"><ReviewerSplitList reviewers={visibleReviewers} activeReviewerId={activeReviewer?.userId ?? null} onSelect={(reviewer) => setActiveReviewerId(reviewer.userId)} multiSelect={regionalCampaignMode} selectedIds={selectedIds} onToggleSelect={toggleSelect} onToggleSelectAll={toggleSelectAll} scope={scopeFilter} /><Pagination page={page} pageCount={pageCount} pageStart={pageStart} total={filteredReviewers.length} onPage={setPage} /></div>
          <div className="xl:sticky xl:top-20">{activeReviewer ? <ReviewerSplitPanel key={activeReviewer.userId} reviewer={activeReviewer} scope={scopeFilter} /> : null}</div>
        </div>
      )}

      {regionalCampaignMode && <div className="mt-3 flex flex-wrap items-center gap-3 rounded-xl border border-[#DDE4DF] bg-white px-4 py-2.5"><div className="min-w-0 flex-1"><span className="text-[10px] font-bold text-[#718078]">캠페인 대상</span><p className="truncate text-sm font-black text-[#17211D]">{selectedIds.size.toLocaleString()}명 선택</p></div><Link to={campaignHref} className="flex min-h-10 min-w-[190px] items-center justify-center rounded-lg bg-[#075C45] px-5 text-xs font-black text-white">캠페인 설계로 이동 →</Link></div>}
      <footer className="mt-4 border-t border-[#E3E8E5] pt-2 text-[9px] text-[#718078]">{summary.modelVersion} 실데이터 · {SCOPE_LABELS[scopeFilter]} {scopedReviewers.length.toLocaleString()}명 · 모델 점수는 확률이 아닌 운영 우선순위입니다.</footer>
    </section>
  );
}

function Pagination({ page, pageCount, pageStart, total, onPage }) {
  const pages = Array.from(new Set([1, page - 1, page, page + 1, pageCount].filter((value) => value >= 1 && value <= pageCount))).sort((a, b) => a - b);
  return <div className="mt-2 flex items-center justify-between rounded-xl border border-[#E3E8E5] bg-white px-4 py-2 text-xs"><div className="flex items-center gap-1"><button type="button" disabled={page === 1} onClick={() => onPage(page - 1)} className="grid h-8 w-8 place-items-center rounded border border-[#DDE4DF] disabled:opacity-35">‹</button>{pages.map((value, index) => <span key={value} className="flex items-center gap-1">{index > 0 && value - pages[index - 1] > 1 && <span>…</span>}<button type="button" onClick={() => onPage(value)} className={`grid h-8 min-w-8 place-items-center rounded px-2 font-bold ${value === page ? "bg-[#075C45] text-white" : "hover:bg-[#F1F4F1]"}`}>{value}</button></span>)}<button type="button" disabled={page === pageCount} onClick={() => onPage(page + 1)} className="grid h-8 w-8 place-items-center rounded border border-[#DDE4DF] disabled:opacity-35">›</button></div><span className="text-[#626D67]">{Math.min(pageStart + 1, total).toLocaleString()}–{Math.min(pageStart + PAGE_SIZE, total).toLocaleString()} / {total.toLocaleString()}</span></div>;
}

export default ReviewerListPage;
