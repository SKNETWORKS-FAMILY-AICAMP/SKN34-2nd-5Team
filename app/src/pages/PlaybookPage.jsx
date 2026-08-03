import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";

import DataModeBadge from "../components/DataModeBadge";
import PageHeader from "../components/common/PageHeader";
import Skeleton from "../components/common/Skeleton";
import ErrorState from "../components/common/ErrorState";
import IndividualInterventionPanel from "../components/playbook/IndividualInterventionPanel";
import RegionalCampaignBuilder from "../components/playbook/RegionalCampaignBuilder";
import GlobalWorkflowStepper from "../components/workflow/GlobalWorkflowStepper";
import {
  useOperationsSummary,
  useReviewers,
  useRiskTypes,
} from "../context/operations-context";
import { useDecisions } from "../context/DecisionContext";
import {
  formatTopPercent,
  loadPlaybooks,
  loadReviewerRecommendations,
  strategyFor,
} from "../data";
import {
  createTargetList,
  deleteTargetList,
  loadTargetLists,
} from "../services/targetListService";
import { DECISION_TONES } from "../data/decisionTones";
import { createActionPlan, loadActionPlans } from "../services/actionPlanService";

// Which playbook a reviewer falls into before anyone has judged them.
const judgmentToDecision = {
  "유지 우세": "변화 지켜보기",
  "약화 우세": "리뷰 활동 늘리기",
  "중단 우세": "리뷰 다시 시작 유도",
};

const decisionToState = {
  "변화 지켜보기": 0,
  "리뷰 활동 늘리기": 1,
  "리뷰 다시 시작 유도": 2,
};

function operationWorkflowSteps({ targetHref, evidenceHref }) {
  return [
    { label: "운영 신호 확인", href: "/" },
    { label: "대상 선정", href: targetHref },
    { label: "근거 검토·판단", href: evidenceHref },
    { label: "운영안 설계" },
    { label: "실행·성과 추적", href: "/operations-history" },
  ];
}

function PlaybookPage() {
  const operationsSummary = useOperationsSummary();
  const reviewers = useReviewers();
  const riskTypes = useRiskTypes();
  const { decisions } = useDecisions();
  const [searchParams] = useSearchParams();
  const contextUserId = searchParams.get("reviewer");
  const contextRegion = searchParams.get("region");

  const [riskTypeFilter, setRiskTypeFilter] = useState("전체");
  const [targetLists, setTargetLists] = useState([]);
  const [actionPlans, setActionPlans] = useState([]);
  const [lastSavedPlanId, setLastSavedPlanId] = useState(null);
  const [designQueueMode, setDesignQueueMode] = useState("individual");
  const [selectedDesignKey, setSelectedDesignKey] = useState(null);
  const [listNameDraft, setListNameDraft] = useState("");
  const [listFeedback, setListFeedback] = useState("");
  const [listFeedbackTone, setListFeedbackTone] = useState("success");
  const [campaignSignal, setCampaignSignal] = useState(searchParams.get("riskType") ?? "전체");
  const showLegacyCampaign = new URLSearchParams(window.location.search).has("legacy");
  const requestedMemberIds = useMemo(
    () => new Set((searchParams.get("members") ?? "").split(",").filter(Boolean)),
    [searchParams],
  );

  useEffect(() => {
    let cancelled = false;
    loadTargetLists()
      .then(({ items }) => {
        if (!cancelled) setTargetLists(items);
      })
      .catch(() => {
        // Target lists are supplementary — the playbook screen must not break.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadActionPlans()
      .then(({ items }) => {
        if (!cancelled) setActionPlans(items ?? []);
      })
      .catch(() => {
        // The design queue remains usable even when saved-plan history is unavailable.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // playbooks 기본값은 []로 둬서, 로딩 중에도 아래 useMemo들이 안전하게
  // 돈다. 실제 로딩/에러 표시는 훅 순서 끝(visiblePlaybooks 뒤)에서 가드.
  const [playbooks, setPlaybooks] = useState([]);
  const [loadStatus, setLoadStatus] = useState("loading");
  const [loadError, setLoadError] = useState(null);
  const [recommendationData, setRecommendationData] = useState(null);

  useEffect(() => {
    let cancelled = false;

    loadPlaybooks()
      .then((data) => {
        if (cancelled) return;
        setPlaybooks(data);
        setLoadStatus("ready");
      })
      .catch((error) => {
        if (!cancelled) {
          setLoadError(error.message);
          setLoadStatus("error");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!contextUserId) return undefined;

    loadReviewerRecommendations(contextUserId)
      .then((data) => {
        if (!cancelled && data.available) setRecommendationData(data);
      })
      .catch(() => {
        // Optional v05 data must not block the existing playbook workflow.
      });
    return () => {
      cancelled = true;
    };
  }, [contextUserId]);

  const reviewersWithDecisions = useMemo(
    () =>
      reviewers.map((reviewer) => ({
        ...reviewer,
        managerDecision: decisions[reviewer.userId]?.decision ?? null,
        // Undecided reviewers are routed by the model's judgment instead —
        // used to place cards/tables, never as a stand-in for a real decision.
        effectiveDecision:
          decisions[reviewer.userId]?.decision ??
          judgmentToDecision[reviewer.modelJudgment],
      })),
    [decisions, reviewers],
  );

  const pendingCount = reviewersWithDecisions.filter(
    (reviewer) => !reviewer.managerDecision,
  ).length;

  const contextReviewer = contextUserId
    ? reviewersWithDecisions.find(
        (reviewer) => reviewer.userId === contextUserId,
      )
    : null;
  const contextStrategy = contextReviewer
    ? contextReviewer.effectiveDecision === "이번엔 제외"
      ? { title: "개입 보류", description: "관리자 판단에 따라 이번 운영 대상에서는 제외합니다. 추가 신호가 확인될 때 다시 검토합니다.", secondary: "추가 개입 없이 변화 관찰", channel: "운영자 검토" }
      : strategyFor(decisionToState[contextReviewer.effectiveDecision] ?? contextReviewer.predictedState, contextReviewer.riskType)
    : null;

  const campaignCandidates = useMemo(() => {
    if (!contextRegion) return [];
    return reviewersWithDecisions
      .filter((reviewer) => reviewer.region === contextRegion)
      .filter((reviewer) => reviewer.crmTarget)
      .filter((reviewer) => reviewer.managerDecision !== "이번엔 제외")
      .filter((reviewer) => requestedMemberIds.size === 0 || requestedMemberIds.has(reviewer.userId))
      .filter((reviewer) => campaignSignal === "전체" || reviewer.riskType === campaignSignal)
      .sort((first, second) => first.priorityRank - second.priorityRank);
  }, [campaignSignal, contextRegion, requestedMemberIds, reviewersWithDecisions]);

  // A. Actual manager judgments from the server, with
  // undecided reviewers counted as their own "미검토" bucket rather than
  // folded into the model's routing — keeps this an honest judgment tally.
  const managerDecisionCounts = useMemo(() => {
    const counts = new Map();

    reviewersWithDecisions.forEach((reviewer) => {
      const key = reviewer.managerDecision ?? "미검토";
      counts.set(key, (counts.get(key) ?? 0) + 1);
    });

    return counts;
  }, [reviewersWithDecisions]);

  const managerDecisionCategories = [
    "리뷰 다시 시작 유도",
    "리뷰 활동 늘리기",
    "변화 지켜보기",
    "이번엔 제외",
    "미검토",
  ];

  const managerMaxCount = Math.max(
    ...managerDecisionCategories.map(
      (category) => managerDecisionCounts.get(category) ?? 0,
    ),
    1,
  );

  // B. Only undecided reviewers, routed by model judgment — a temporary
  // placeholder distribution, not a manager decision or confirmed campaign.
  const pendingModelRouteCounts = useMemo(() => {
    const counts = new Map();

    reviewersWithDecisions
      .filter((reviewer) => !reviewer.managerDecision)
      .forEach((reviewer) => {
        const key = judgmentToDecision[reviewer.modelJudgment];
        counts.set(key, (counts.get(key) ?? 0) + 1);
      });

    return counts;
  }, [reviewersWithDecisions]);

  const modelRoutedDecisions = playbooks.filter((playbook) =>
    Object.values(judgmentToDecision).includes(playbook.decision),
  );

  const modelRouteMaxCount = Math.max(
    ...modelRoutedDecisions.map(
      (playbook) => pendingModelRouteCounts.get(playbook.decision) ?? 0,
    ),
    1,
  );

  const visiblePlaybooks = useMemo(() => {
    if (!contextReviewer) {
      return playbooks;
    }

    // Deep-linked from a reviewer: lead with their playbook, keep the rest.
    return [...playbooks].sort((first, second) => {
      const firstMatch = first.decision === contextReviewer.effectiveDecision;
      const secondMatch = second.decision === contextReviewer.effectiveDecision;
      return Number(secondMatch) - Number(firstMatch);
    });
  }, [contextReviewer, playbooks]);

  if (!contextRegion && !contextUserId && loadStatus === "error") {
    return <ErrorState message={loadError} />;
  }

  if (!contextRegion && !contextUserId && loadStatus === "loading") {
    return <Skeleton rows={6} columns={3} />;
  }

  async function handleSaveTargetList(decision, pool) {
    const name = listNameDraft.trim() || `${decision} · ${new Date().toLocaleDateString("ko-KR")}`;
    try {
      const saved = await createTargetList({
        name,
        decision,
        modelVersion: operationsSummary.modelVersion,
        members: pool.map((reviewer) => ({
          userId: reviewer.userId,
          sampleId: reviewer.sampleId,
        })),
      });
      setTargetLists((current) => [saved, ...current]);
      setListNameDraft("");
      setListFeedbackTone("success");
      setListFeedback(
        `"${saved.name}" 명단에 ${saved.memberCount.toLocaleString()}명 저장됨` +
          (saved.duplicatesRemoved > 0
            ? ` · 중복 ${saved.duplicatesRemoved}명 자동 제외`
            : ""),
      );
      return saved;
    } catch (error) {
      setListFeedbackTone("error");
      setListFeedback(error.message);
      throw error;
    }
  }

  async function saveRegionalPlan(plan) {
    const list = await handleSaveTargetList(`권역 캠페인 · ${contextRegion}`, campaignCandidates);
    const savedPlan = await createActionPlan({
      planType: "regional", modelVersion: operationsSummary.modelVersion,
      regionCode: contextRegion, targetListId: list.listId,
      managerDecision: null, status: "saved", ...plan,
    });
    setActionPlans((current) => [savedPlan, ...current.filter((item) => item.planId !== savedPlan.planId)]);
    setLastSavedPlanId(savedPlan.planId);
    setListFeedback((current) => `${current} · 캠페인 실행안 저장됨`);
    return savedPlan;
  }

  async function saveIndividualPlan(plan) {
    const list = await handleSaveTargetList(`개인 특별 관리 · ${contextReviewer.userId}`, [contextReviewer]);
    const savedPlan = await createActionPlan({
      planType: "individual", modelVersion: operationsSummary.modelVersion,
      reviewerUserId: contextReviewer.userId, sampleId: contextReviewer.sampleId,
      targetListId: list.listId, managerDecision: contextReviewer.managerDecision ?? contextReviewer.effectiveDecision,
      status: "saved", ...plan,
    });
    setActionPlans((current) => [savedPlan, ...current.filter((item) => item.planId !== savedPlan.planId)]);
    setLastSavedPlanId(savedPlan.planId);
    setListFeedback((current) => `${current} · 개인 실행안 저장됨`);
    return savedPlan;
  }

  async function handleDeleteTargetList(listId) {
    try {
      await deleteTargetList(listId);
      setTargetLists((current) => current.filter((list) => list.listId !== listId));
    } catch (error) {
      setListFeedbackTone("error");
      setListFeedback(error.message);
    }
  }

  function downloadListCsv(list) {
    const rows = list.memberUserIds.map((userId) => [userId]);
    const csv = [["user_id"], ...rows]
      .map((row) => row.map((v) => `"${String(v).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const bom = String.fromCharCode(0xfeff);
    const blob = new Blob([bom + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${list.name}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function matchingReviewers(decision) {
    let pool = reviewersWithDecisions.filter(
      (reviewer) => reviewer.effectiveDecision === decision,
    );

    if (riskTypeFilter !== "전체") {
      pool = pool.filter((reviewer) => reviewer.riskType === riskTypeFilter);
    }

    if (contextRegion) {
      pool = pool.filter((reviewer) => reviewer.region === contextRegion);
    }

    return pool.sort(
      (first, second) => first.priorityRank - second.priorityRank,
    );
  }

  if (contextRegion) {
    const regionalQueueHref = `/reviewers?mode=regional&region=${encodeURIComponent(contextRegion)}`;
    return (
      <section className="pb-5">
        <GlobalWorkflowStepper steps={operationWorkflowSteps({ targetHref: regionalQueueHref, evidenceHref: regionalQueueHref })} currentStep={4} />

        <RegionalCampaignBuilder
          region={contextRegion}
          topCity={campaignCandidates[0]?.topCity}
          candidates={campaignCandidates}
          riskTypes={riskTypes}
          selectedSignal={campaignSignal}
          onSignalChange={setCampaignSignal}
          onSave={saveRegionalPlan}
        />

        {listFeedback && (
          <div className={`mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl px-4 py-3 text-sm font-bold ${listFeedbackTone === "error" ? "bg-[#FCE8E3] text-[#9F321F]" : "bg-[#E3F1EA] text-[#075C45]"}`}>
            <span>{listFeedback}</span>
            {lastSavedPlanId && <Link to={`/operations-history?tab=plans&planId=${encodeURIComponent(lastSavedPlanId)}`} className="rounded-lg border border-current px-3 py-2 text-xs">운영 결과·알림에서 확인 →</Link>}
          </div>
        )}

        <footer className="mt-8 border-t border-[#DDE4DF] pt-4 text-xs leading-5 text-[#718078]">저장한 명단은 운영 검토용이며 캠페인 효과를 확정하지 않습니다. 30·60·90일 비교 관찰 후 다음 판단에 반영합니다.</footer>
      </section>
    );
  }

  if (contextReviewer && contextStrategy) {
    const individualQueueHref = "/reviewers?mode=individual&status=미검토&sort=우선순위";
    const reviewerHref = `/reviewers/${encodeURIComponent(contextReviewer.userId)}?source=core`;
    return (
      <section className="-mx-4 -my-5 min-h-[calc(100vh-3.5rem)] bg-white px-4 py-3 pb-5 sm:-mx-5 sm:px-5 md:-mx-6 md:px-6 xl:-mx-7 xl:px-7">
        <GlobalWorkflowStepper steps={operationWorkflowSteps({ targetHref: individualQueueHref, evidenceHref: reviewerHref })} currentStep={4} />

        <IndividualInterventionPanel
          reviewer={contextReviewer}
          recommendationData={recommendationData}
          strategy={contextStrategy}
          onSave={saveIndividualPlan}
        />

        {listFeedback && <div className={`mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl px-4 py-3 text-sm font-bold ${listFeedbackTone === "error" ? "bg-[#FCE8E3] text-[#9F321F]" : "bg-[#E3F1EA] text-[#075C45]"}`}><span>{listFeedback}</span>{lastSavedPlanId && <Link to={`/operations-history?tab=plans&planId=${encodeURIComponent(lastSavedPlanId)}`} className="rounded-lg border border-current px-3 py-2 text-xs">운영 결과·알림에서 확인 →</Link>}</div>}

        <footer className="mt-8 border-t border-[#DDE4DF] pt-4 text-xs leading-5 text-[#718078]">개입안은 검증된 처방이 아니며 의학적 상태를 뜻하지 않습니다. 실제 실행 전 운영자 검토와 30·60·90일 관찰이 필요합니다.</footer>
      </section>
    );
  }

  if (!contextRegion && !contextReviewer) {
    const plannedReviewerIds = new Set(actionPlans.filter((plan) => plan.planType === "individual" && plan.status !== "archived").map((plan) => plan.reviewerUserId));
    const plannedTargetListIds = new Set(actionPlans.filter((plan) => plan.status !== "archived").map((plan) => plan.targetListId));
    const personalDesignQueue = reviewersWithDecisions
      .filter((reviewer) => reviewer.managerDecision && reviewer.managerDecision !== "이번엔 제외")
      .filter((reviewer) => !plannedReviewerIds.has(reviewer.userId))
      .sort((first, second) => first.priorityRank - second.priorityRank);
    const regionalDesignQueue = targetLists.filter((list) => list.name.startsWith("권역 캠페인 · ") && !plannedTargetListIds.has(list.listId));
    const personalQueueItems = personalDesignQueue.map((reviewer) => ({ key: `individual:${reviewer.userId}`, type: "individual", reviewer, title: reviewer.userId, decision: reviewer.managerDecision, signal: reviewer.riskType, href: `/playbook?mode=individual&reviewer=${encodeURIComponent(reviewer.userId)}` }));
    const regionalQueueItems = regionalDesignQueue.map((list) => { const region = regionFromTargetList(list); return { key: `regional:${list.listId}`, type: "regional", list, title: region, decision: "지역 활성화 캠페인", signal: list.decision, href: `/playbook?mode=region&region=${encodeURIComponent(region)}` }; });
    const activeQueueItems = designQueueMode === "individual" ? personalQueueItems : regionalQueueItems;
    const selectedDesign = activeQueueItems.find((item) => item.key === selectedDesignKey) ?? activeQueueItems[0] ?? null;
    const planGroups = new Map();
    [...actionPlans].sort((first, second) => new Date(second.updatedAt) - new Date(first.updatedAt)).forEach((plan) => {
      const target = plan.reviewerUserId ?? plan.regionCode ?? "대상 미지정";
      const key = `${plan.planType}:${target}`;
      const group = planGroups.get(key);
      if (group) group.count += 1;
      else planGroups.set(key, { key, target, count: 1, latest: plan });
    });
    const recentPlanGroups = [...planGroups.values()].slice(0, 4);
    const savedTargetCount = planGroups.size;
    return (
      <section className="-mx-4 -my-5 min-h-[calc(100vh-3.5rem)] bg-white px-4 py-3 pb-5 sm:-mx-5 sm:px-5 md:-mx-6 md:px-6 xl:-mx-7 xl:px-7">
        <GlobalWorkflowStepper steps={operationWorkflowSteps({ targetHref: "/reviewers?mode=individual&status=미검토&sort=우선순위", evidenceHref: "/reviewers?mode=individual&status=미검토&sort=우선순위" })} currentStep={4} />

        <DesignSummary personalPending={personalDesignQueue.length} regionalPending={regionalDesignQueue.length} savedTargets={savedTargetCount} planVersions={actionPlans.length} />

        <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1.55fr)_minmax(390px,0.95fr)]">
          <DesignQueueTable mode={designQueueMode} onModeChange={(mode) => { setDesignQueueMode(mode); setSelectedDesignKey(null); }} personalCount={personalQueueItems.length} regionalCount={regionalQueueItems.length} items={activeQueueItems} selectedKey={selectedDesign?.key} onSelect={setSelectedDesignKey} />
          <SelectedDesignPanel item={selectedDesign} />
        </div>

        <RecentPlanTable groups={recentPlanGroups} />

        <details className="mt-3 rounded-xl border border-[#DDE4DF] bg-white px-4 py-3">
          <summary className="cursor-pointer text-sm font-black text-[#17211D]">운영 전략 기준 보기</summary>
          <div className="mt-3 grid gap-2 border-t border-[#EDF0EE] pt-3 md:grid-cols-2 xl:grid-cols-4">
            {playbooks.map((playbook) => {
              const count = managerDecisionCounts.get(playbook.decision) ?? 0;
              return <article key={playbook.decision} className="rounded-lg bg-[#F7F9F7] p-3"><span className="text-[10px] font-black text-[#137A5A]">{count.toLocaleString()}명 판단</span><h3 className="mt-1 text-sm font-black">{playbook.decision}</h3><p className="mt-1 text-[11px] leading-5 text-[#626D67]">{playbook.primaryAction}</p></article>;
            })}
          </div>
        </details>

        <footer className="mt-8 border-t border-[#DDE4DF] pt-4 text-xs leading-5 text-[#718078]">캠페인과 개입안은 검증된 처방이 아니며 실제 발송·실행 전 운영자 검토가 필요합니다.</footer>
      </section>
    );
  }

  return (
    <section>
      <PageHeader
        title="리텐션 플레이북"
        description="관리자 판단별로 어떤 조치를 검토할지 정리했습니다. 아직 판단하지 않은 리뷰어는 모델 판단 기준으로 분류됩니다."
        meta={<DataModeBadge />}
      />

      {contextRegion && (
        <RegionalCampaignBuilder
          region={contextRegion}
          topCity={campaignCandidates[0]?.topCity}
          candidates={campaignCandidates}
          riskTypes={riskTypes}
          selectedSignal={campaignSignal}
          onSignalChange={setCampaignSignal}
          onSave={() => handleSaveTargetList(`권역 캠페인 · ${contextRegion}`, campaignCandidates)}
        />
      )}

      {contextReviewer && contextStrategy && (
        <IndividualInterventionPanel
          reviewer={contextReviewer}
          recommendationData={recommendationData}
          strategy={contextStrategy}
          onSave={() => handleSaveTargetList(`개인 개입 · ${contextReviewer.userId}`, [contextReviewer])}
        />
      )}

      {contextRegion && showLegacyCampaign && (
        <section className="mt-6 rounded-xl border border-[#B7D8C8] bg-[#F8FBF9] p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold tracking-wider text-[#137A5A]">권역 캠페인 설계 · 1/4</p>
              <h2 className="mt-1 text-xl font-bold text-[#17211D]">{contextRegion} 권역 리텐션 캠페인</h2>
              <p className="mt-2 text-sm leading-6 text-[#626D67]">
                state 기준 활동 지역으로 후보를 좁힙니다. 이 화면은 발송을 실행하지 않으며, 저장한 명단은 운영 검토용입니다.
              </p>
            </div>
            <Link to={`/reviewers?region=${encodeURIComponent(contextRegion)}`} className="text-sm font-medium text-[#137A5A] underline">
              권역 리뷰어 다시 보기
            </Link>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-4">
            <CampaignStep number="1" label="권역" value={contextRegion} />
            <CampaignStep number="2" label="대상 조건" value="CRM 상위 20% · 제외 판단 제외" />
            <CampaignStep number="3" label="선택 후보" value={`${campaignCandidates.length.toLocaleString()}명`} />
            <CampaignStep number="4" label="검증 상태" value="A/B 검증 필요" />
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-[#626D67]">집중할 위험 신호</span>
            {["전체", ...riskTypes].map((signal) => (
              <button
                key={signal}
                type="button"
                onClick={() => setCampaignSignal(signal)}
                className={`min-h-10 rounded-full border px-3 text-xs font-medium ${campaignSignal === signal ? "border-[#137A5A] bg-[#E3F1EA] text-[#137A5A]" : "border-[#DDE4DF] text-[#626D67]"}`}
              >
                {signal}
              </button>
            ))}
          </div>

          <div className="mt-5 grid gap-3 lg:grid-cols-3">
            <CampaignDetail title="운영 가설" text={campaignSignal === "탐색 활동 축소형" ? "새로운 음식점 탐색과 리뷰 작성의 재개를 돕는 지역 미션을 검토합니다." : "리뷰 활동 재개를 돕는 권역별 개입안을 검토합니다."} />
            <CampaignDetail title="기대 효과 표현" text="수치 상승을 약속하지 않습니다. 실제 증분 효과는 비교군을 둔 A/B 검증 후에만 판단합니다." />
            <CampaignDetail title="측정 계획" text="30·60·90일 동안 리뷰 수, 활동 월, 신규 음식점 리뷰 수와 재방문 여부를 관찰합니다." />
          </div>

          {campaignCandidates.length > 0 && (
            <button
              type="button"
              onClick={() => handleSaveTargetList(`권역 캠페인 · ${contextRegion}`, campaignCandidates)}
              className="mt-5 min-h-10 rounded-lg bg-[#137A5A] px-4 text-sm font-bold text-white hover:bg-[#185C46]"
            >
              {campaignCandidates.length.toLocaleString()}명 운영 검토 명단 저장
            </button>
          )}
        </section>
      )}

      {contextReviewer && showLegacyCampaign && (
        <div className="mt-6 rounded-xl border border-[#137A5A] bg-[#E3F1EA] p-5">
          <p className="text-xs font-bold tracking-widest text-[#137A5A]">
            현재 리뷰어에게 추천
          </p>

          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Link
              to={`/reviewers/${contextReviewer.userId}`}
              className="font-bold text-[#17211D] underline"
            >
              {contextReviewer.userId}
            </Link>

            <span
              className="rounded bg-white px-2 py-1 text-xs text-[#626D67]"
              title="통합 우선순위 기준 순위입니다 — 중단·약화 점수를 합친 상대 검토 순위이며 보정된 이탈 확률이 아닙니다."
            >
              {contextReviewer.priorityRank}위 · 상위{" "}
              {formatTopPercent(contextReviewer.priorityTopPercent)}
            </span>

            <span className="rounded bg-white px-2 py-1 text-xs text-[#626D67]">
              {contextReviewer.modelJudgment}
            </span>

            <span className="rounded bg-white px-2 py-1 text-xs text-[#626D67]">
              {contextReviewer.riskType}
            </span>
          </div>

          <p className="mt-3 text-sm text-[#17211D]">
            {contextReviewer.managerDecision
              ? `관리자 판단 "${contextReviewer.managerDecision}" 기준 플레이북을 먼저 표시합니다.`
              : `아직 판단 전이라 모델 판단 기준으로 "${contextReviewer.effectiveDecision}" 플레이북을 먼저 표시합니다.`}
          </p>

          {recommendationData?.sampleId === contextReviewer.sampleId &&
            recommendationData.recommendations.length > 0 && (
            <div className="mt-5 border-t border-[#B7D8C8] pt-4">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div>
                  <p className="text-sm font-bold text-[#17211D]">관심 카테고리 기반 탐방 후보</p>
                  <p className="mt-1 text-xs text-[#4B665B]">
                    미방문 음식점과 기존 리뷰 활동 반경을 바탕으로 찾은 운영 참고 후보입니다.
                  </p>
                </div>
                <span className="text-[11px] text-[#4B665B]">방문 또는 리뷰 작성을 예측하지 않습니다</span>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                {recommendationData.recommendations.map((restaurant) => (
                  <article key={restaurant.businessId} className="rounded-lg border border-[#B7D8C8] bg-white p-4">
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs font-bold text-[#137A5A]">후보 {restaurant.rank}</span>
                      <span className="text-xs text-[#626D67]">약 {restaurant.distanceKm}km</span>
                    </div>
                    <h3 className="mt-2 font-bold text-[#17211D]">{restaurant.name}</h3>
                    <p className="mt-1 text-xs text-[#626D67]">{restaurant.city}, {restaurant.state} · Yelp {restaurant.stars.toFixed(1)} · 리뷰 {restaurant.reviewCount.toLocaleString()}개</p>
                    <p className="mt-3 text-xs leading-5 text-[#356A78]">
                      관심 카테고리 · {restaurant.primaryCategory}
                    </p>
                  </article>
                ))}
              </div>
            </div>
            )}
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <div>
          {/* This counts across the full cohort, not just the top-20%
              target population — the "미검토" bucket only makes sense read
              that way, so the label must match, not the mockup's claim. */}
          <h2 className="text-lg font-medium text-[#17211D]">
            전체 {reviewersWithDecisions.length.toLocaleString()}명의 관리자
            판단 현황
          </h2>

          <p className="mt-2 text-sm text-[#626D67]">
            이 브라우저에 저장된 실제 판단만 집계합니다.
          </p>

          <div className="mt-4 rounded-xl border border-[#DDE4DF] bg-white p-5">
            {managerDecisionCategories.map((category) => {
              const count = managerDecisionCounts.get(category) ?? 0;

              return (
                <div
                  key={category}
                  className="flex items-center gap-4 border-b border-[#DDE4DF] py-3 last:border-b-0"
                >
                  <span className="w-40 shrink-0 text-sm text-[#17211D]">
                    {category}
                  </span>

                  <div className="h-2 flex-1 rounded-full bg-[#F1F4F1]">
                    <div
                      className="h-2 rounded-full bg-[#137A5A]"
                      style={{
                        width: `${(count / managerMaxCount) * 100}%`,
                      }}
                    />
                  </div>

                  <span className="w-16 shrink-0 text-right text-sm font-bold text-[#17211D]">
                    {count.toLocaleString()}명
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div>
          <h2 className="text-lg font-medium text-[#17211D]">
            미검토 리뷰어 {pendingCount.toLocaleString()}명의 모델 기준 추천
            경로
          </h2>

          <p className="mt-2 text-sm text-[#626D67]">
            관리자 판단 전 임시 추천입니다 — 모델 판단을 실제 판단이나 확정
            캠페인으로 보지 마세요.
          </p>

          <div className="mt-4 rounded-xl border border-[#DDE4DF] bg-white p-5">
            {modelRoutedDecisions.map((playbook) => {
              const count =
                pendingModelRouteCounts.get(playbook.decision) ?? 0;

              return (
                <div
                  key={playbook.decision}
                  className="flex items-center gap-4 border-b border-[#DDE4DF] py-3 last:border-b-0"
                >
                  <span className="w-40 shrink-0 text-sm text-[#17211D]">
                    {playbook.decision}
                  </span>

                  <div className="h-2 flex-1 rounded-full bg-[#F1F4F1]">
                    <div
                      className="h-2 rounded-full bg-[#4C987C]"
                      style={{
                        width: `${(count / modelRouteMaxCount) * 100}%`,
                      }}
                    />
                  </div>

                  <span className="w-16 shrink-0 text-right text-sm font-bold text-[#17211D]">
                    {count.toLocaleString()}명
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-[#626D67]">위험 유형</span>

        {["전체", ...riskTypes].map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setRiskTypeFilter(option)}
            className={[
              "rounded-full border px-3 py-1 text-xs font-bold transition",
              riskTypeFilter === option
                ? "border-[#137A5A] bg-[#E3F1EA] text-[#137A5A]"
                : "border-[#DDE4DF] text-[#626D67] hover:border-[#137A5A]",
            ].join(" ")}
          >
            {option}
          </button>
        ))}
      </div>

      <div className="mt-6 grid gap-6">
        {visiblePlaybooks.map((playbook) => {
          const pool = matchingReviewers(playbook.decision);
          const managerJudgedCount = pool.filter(
            (reviewer) => reviewer.managerDecision === playbook.decision,
          ).length;
          const modelRoutedCount = pool.length - managerJudgedCount;
          const isRecommended =
            contextReviewer &&
            playbook.decision === contextReviewer.effectiveDecision;
          const subStrategy = playbook.subStrategy.find(
            (item) => item.riskType === riskTypeFilter,
          );

          return (
            <div
              key={playbook.decision}
              className={[
                "rounded-xl border bg-white p-6",
                isRecommended
                  ? "border-[#137A5A] ring-2 ring-[#137A5A]/20"
                  : "border-[#DDE4DF]",
              ].join(" ")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-xl font-bold text-[#17211D]">
                      {playbook.decision}
                    </h2>

                    {isRecommended && (
                      <span className="rounded-full bg-[#137A5A] px-2 py-1 text-xs font-bold text-white">
                        현재 리뷰어 추천
                      </span>
                    )}

                    {playbook.modelJudgment && (
                      <span
                        className={`rounded px-2 py-1 text-xs font-bold ${
                          DECISION_TONES[playbook.decision] ?? ""
                        }`}
                      >
                        모델 {playbook.modelJudgment}
                      </span>
                    )}
                  </div>

                  <p className="mt-3 max-w-3xl text-sm leading-6 text-[#626D67]">
                    {playbook.condition}
                  </p>
                </div>

                <span className="whitespace-nowrap rounded-full bg-[#F1F4F1] px-3 py-1 text-xs font-bold text-[#626D67]">
                  {pool.length.toLocaleString()}명 해당
                </span>
              </div>

              <p className="mt-2 text-xs text-[#626D67]">
                관리자 판단 {managerJudgedCount.toLocaleString()}명 · 미검토
                모델 추천 {modelRoutedCount.toLocaleString()}명
              </p>

              <div className="mt-5 grid gap-3 border-t border-[#DDE4DF] pt-4 text-sm sm:grid-cols-2">
                <Row label="확인 신호" value={playbook.signals} />
                <Row label="검토할 조치" value={playbook.primaryAction} />
                <Row label="채널" value={playbook.channel} />
                <Row label="성과 측정 초안" value={playbook.successDraft} />
              </div>

              {subStrategy && (
                <p className="mt-4 rounded-lg bg-[#E3F1EA] px-4 py-3 text-sm text-[#137A5A]">
                  {riskTypeFilter} · {subStrategy.text}
                </p>
              )}

              {pool.length > 0 && (
                <button
                  type="button"
                  onClick={() => handleSaveTargetList(playbook.decision, pool)}
                  className="mt-4 min-h-9 rounded-lg border border-[#DDE4DF] px-3 text-xs font-medium text-[#137A5A] transition hover:border-[#137A5A] hover:bg-[#E3F1EA]"
                >
                  이 {pool.length.toLocaleString()}명을 대상 명단에 추가
                </button>
              )}

              {pool.length > 0 && (
                <div className="mt-5">
                  <p className="text-xs font-semibold text-[#626D67]">
                    이 판단에 해당하는 리뷰어 · 상위 10명
                  </p>

                  <div className="mt-3 overflow-x-auto">
                    <table className="min-w-[560px] text-sm">
                      <thead>
                        <tr className="text-left text-xs text-[#626D67]">
                          <th className="py-2 pr-4">순위</th>
                          <th className="py-2 pr-4">리뷰어</th>
                          <th className="py-2 pr-4">모델 판단</th>
                          <th className="py-2">위험 유형</th>
                        </tr>
                      </thead>

                      <tbody>
                        {pool.slice(0, 10).map((reviewer) => (
                          <tr
                            key={reviewer.userId}
                            className="border-t border-[#DDE4DF]"
                          >
                            <td className="py-2 pr-4 text-[#626D67]">
                              {reviewer.priorityRank}위
                            </td>

                            <td className="py-2 pr-4">
                              <Link
                                to={`/reviewers/${reviewer.userId}`}
                                className="font-semibold text-[#137A5A]"
                              >
                                {reviewer.userId}
                              </Link>
                            </td>

                            <td className="py-2 pr-4 text-[#626D67]">
                              {reviewer.modelJudgment}
                            </td>

                            <td className="py-2 text-[#626D67]">
                              {reviewer.riskType}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-10 rounded-lg border border-[#DDE4DF] bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-medium text-[#17211D]">대상 명단</h2>
          <span className="text-xs text-[#626D67]">
            CRM 툴로 넘길 명단을 저장 · 발송 기능이 아닙니다
          </span>
        </div>

        <div className="mt-3 flex gap-2">
          <input
            type="text"
            value={listNameDraft}
            onChange={(event) => setListNameDraft(event.target.value)}
            placeholder="명단 이름 · 예) 8월 1주차 재참여"
            className="min-h-9 flex-1 rounded-lg border border-[#DDE4DF] px-3 text-sm"
          />
          <span className="self-center text-xs text-[#626D67]">
            각 플레이북 카드의 "대상 명단에 추가" 버튼으로 저장됩니다
          </span>
        </div>

        {listFeedback && (
          <p
            className={`mt-2 text-xs ${
              listFeedbackTone === "error" ? "text-[#8A3B2E]" : "text-[#137A5A]"
            }`}
          >
            {listFeedback}
          </p>
        )}

        {targetLists.length === 0 ? (
          <p className="mt-4 text-sm text-[#626D67]">
            아직 저장된 명단이 없습니다.
          </p>
        ) : (
          <div className="mt-4 divide-y divide-[#F1F4F1]">
            {targetLists.map((list) => (
              <div
                key={list.listId}
                className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm"
              >
                <div>
                  <span className="font-medium text-[#17211D]">
                    {list.name}
                  </span>
                  <span className="ml-2 text-xs text-[#626D67]">
                    {list.memberCount.toLocaleString()}명
                    {list.duplicatesRemoved > 0 &&
                      ` · 중복 ${list.duplicatesRemoved}명 자동 제외`}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => downloadListCsv(list)}
                    className="min-h-10 rounded-lg border border-[#DDE4DF] px-3 text-xs font-medium text-[#137A5A] transition hover:border-[#137A5A] hover:bg-[#E3F1EA]"
                  >
                    CSV 내보내기
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteTargetList(list.listId)}
                    className="min-h-10 rounded-lg border border-[#DDE4DF] px-3 text-xs font-medium text-[#626D67] transition hover:border-[#8A3B2E] hover:text-[#8A3B2E]"
                  >
                    삭제
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs leading-5 text-[#626D67]">
        이 플레이북은 개입 효과가 검증된 처방이 아니며, 의학적 상태를 의미하지
        않습니다 · Reviewer Retention · {operationsSummary.dataModeLabel} data
      </footer>
    </section>
  );
}

function CampaignStep({ number, label, value }) {
  return (
    <div className="rounded-lg border border-[#DDE4DF] bg-white p-4">
      <p className="text-xs font-bold text-[#137A5A]">{number} · {label}</p>
      <p className="mt-2 text-sm font-medium text-[#17211D]">{value}</p>
    </div>
  );
}

function CampaignDetail({ title, text }) {
  return (
    <div className="rounded-lg bg-[#EAF3ED] p-4">
      <p className="text-xs font-bold text-[#137A5A]">{title}</p>
      <p className="mt-2 text-xs leading-5 text-[#356A78]">{text}</p>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div>
      <p className="text-xs font-semibold text-[#626D67]">{label}</p>
      <p className="mt-1 text-[#17211D]">{value}</p>
    </div>
  );
}

function regionFromTargetList(list) {
  const decisionRegion = String(list.decision ?? "").match(/^권역 캠페인 · (.+)$/)?.[1];
  if (decisionRegion) return decisionRegion.trim();
  return String(list.name ?? "").split(" · ")[1]?.trim() || "권역 미지정";
}

function maskReviewerId(userId) {
  const value = String(userId ?? "");
  return value.length > 11 ? `${value.slice(0, 5)}…${value.slice(-4)}` : value;
}

function DesignSummary({ personalPending, regionalPending, savedTargets, planVersions }) {
  const metrics = [
    ["판단 완료·설계 대기", `${personalPending.toLocaleString()}명`],
    ["지역 설계 대기", `${regionalPending.toLocaleString()}건`],
    ["저장된 운영 대상", `${savedTargets.toLocaleString()}개`],
    ["운영안 기록", `${planVersions.toLocaleString()}건`],
  ];
  return <section className="mt-3 grid overflow-hidden rounded-xl border border-[#DDE4DF] bg-white sm:grid-cols-2 xl:grid-cols-4">{metrics.map(([label, value], index) => <div key={label} className={`px-4 py-3 ${index > 0 ? "border-t border-[#E7EBE8] sm:border-l sm:border-t-0" : ""}`}><p className="text-[11px] font-bold text-[#718078]">{label}</p><p className="mt-1 text-xl font-black text-[#17211D]">{value}</p></div>)}</section>;
}

function DesignQueueTable({ mode, onModeChange, personalCount, regionalCount, items, selectedKey, onSelect }) {
  return <section className="overflow-hidden rounded-xl border border-[#DDE4DF] bg-white">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E5EAE6] px-4 py-3">
      <div><p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">DESIGN QUEUE</p><h2 className="mt-0.5 text-base font-black">설계 대기 대상</h2></div>
      <div className="flex rounded-lg border border-[#DDE4DF] bg-[#F7F9F7] p-1 text-xs font-black">
        <button type="button" onClick={() => onModeChange("individual")} className={`rounded-md px-3 py-2 ${mode === "individual" ? "bg-[#075C45] text-white" : "text-[#536159]"}`}>개인 {personalCount}</button>
        <button type="button" onClick={() => onModeChange("regional")} className={`rounded-md px-3 py-2 ${mode === "regional" ? "bg-[#075C45] text-white" : "text-[#536159]"}`}>지역 {regionalCount}</button>
      </div>
    </div>
    <div className="grid grid-cols-[72px_minmax(130px,1.2fr)_minmax(120px,1fr)_minmax(110px,0.9fr)_80px] gap-3 border-b border-[#E5EAE6] bg-[#FAFBFA] px-4 py-2 text-[10px] font-black text-[#718078]"><span>우선순위</span><span>대상</span><span>저장된 판단</span><span>관찰 신호</span><span>상태</span></div>
    {items.length === 0 ? <div className="grid min-h-64 place-items-center px-4 text-sm font-bold text-[#718078]">현재 설계 대기 대상이 없습니다.</div> : <div className="divide-y divide-[#EDF0EE]">{items.slice(0, 7).map((item, index) => {
      const reviewer = item.reviewer;
      const selected = item.key === selectedKey;
      return <button key={item.key} type="button" onClick={() => onSelect(item.key)} className={`grid w-full grid-cols-[72px_minmax(130px,1.2fr)_minmax(120px,1fr)_minmax(110px,0.9fr)_80px] items-center gap-3 border-l-4 px-4 py-3 text-left text-xs ${selected ? "border-[#07855F] bg-[#EDF7F2]" : "border-transparent bg-white hover:bg-[#F8FAF8]"}`}>
        <span className="font-black text-[#9B6500]">{reviewer ? `${reviewer.priorityRank}위` : `${index + 1}번`}</span>
        <span className="min-w-0"><strong className="block truncate text-[#17211D]">{reviewer ? maskReviewerId(reviewer.userId) : item.title}</strong><small className="mt-0.5 block truncate text-[10px] text-[#718078]">{reviewer ? [reviewer.region, reviewer.topCity].filter(Boolean).join(" · ") : `${item.list?.memberCount ?? 0}명 대상`}</small></span>
        <span className="truncate font-bold text-[#075C45]">{item.decision || "미지정"}</span>
        <span className="truncate text-[#536159]">{item.signal || "확인 필요"}</span>
        <span className="rounded-md border border-[#B7D8C8] px-2 py-1 text-center font-bold text-[#075C45]">설계 대기</span>
      </button>;
    })}</div>}
    <div className="flex items-center justify-between border-t border-[#E5EAE6] px-4 py-3 text-[11px] text-[#718078]"><span>우선순위 기준 상위 대상</span><span>{Math.min(items.length, 7)} / {items.length.toLocaleString()}</span></div>
  </section>;
}

function SelectedDesignPanel({ item }) {
  if (!item) return <aside className="grid min-h-[430px] place-items-center rounded-xl border border-[#DDE4DF] bg-white p-6 text-center"><div><p className="text-sm font-black">설계할 대상을 선택하세요.</p><p className="mt-2 text-xs text-[#718078]">관리자 판단이 저장된 대상만 표시됩니다.</p></div></aside>;
  if (item.type === "regional") {
    const list = item.list;
    return <aside className="overflow-hidden rounded-xl border border-[#DDE4DF] bg-white"><div className="border-b border-[#E5EAE6] p-5"><p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">SELECTED REGION</p><h2 className="mt-1 text-xl font-black">{item.title}</h2><p className="mt-1 text-xs text-[#718078]">저장된 지역 대상 명단을 기반으로 캠페인을 설계합니다.</p></div><div className="grid grid-cols-2 border-b border-[#E5EAE6]"><PanelMetric label="대상 인원" value={`${(list.memberCount ?? 0).toLocaleString()}명`} /><PanelMetric label="관리자 판단" value={list.decision || "미지정"} /></div><div className="space-y-3 p-5"><EvidenceRow label="운영 단위" value={item.title} /><EvidenceRow label="모델 기준" value={list.modelVersion || "확인 필요"} /><EvidenceRow label="중복 제외" value={`${(list.duplicatesRemoved ?? 0).toLocaleString()}명`} /><Link to={item.href} className="mt-4 flex min-h-11 items-center justify-center rounded-lg bg-[#075C45] px-4 text-sm font-black text-white">지역 운영안 설계 계속 →</Link></div></aside>;
  }
  const reviewer = item.reviewer;
  const strategy = strategyFor(decisionToState[reviewer.effectiveDecision] ?? reviewer.predictedState, reviewer.riskType);
  return <aside className="overflow-hidden rounded-xl border border-[#DDE4DF] bg-white"><div className="border-b border-[#E5EAE6] p-5"><p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">SELECTED REVIEWER</p><h2 className="mt-1 text-xl font-black">{maskReviewerId(reviewer.userId)}</h2><p className="mt-1 text-xs text-[#718078]">{[reviewer.region, reviewer.topCity].filter(Boolean).join(" · ") || "권역 정보 없음"}</p></div><div className="grid grid-cols-3 border-b border-[#E5EAE6]"><PanelMetric label="우선순위" value={`${reviewer.priorityRank}위`} /><PanelMetric label="관리자 판단" value={reviewer.managerDecision} /><PanelMetric label="위험 유형" value={reviewer.riskType} /></div><div className="p-5"><h3 className="text-sm font-black">판단 근거</h3><div className="mt-3 divide-y divide-[#EDF0EE] rounded-lg border border-[#E2E7E3]"><EvidenceRow label="최근 리뷰 공백" value={`${reviewer.recentRecencyDays ?? 0}일`} /><EvidenceRow label="최근 활동 월" value={`${reviewer.recentActiveMonths ?? 0}개월`} /><EvidenceRow label="핵심 변화" value={reviewer.coreChange || reviewer.riskType} /></div><div className="mt-4 rounded-lg bg-[#EEF7F2] p-4"><p className="text-[10px] font-black tracking-[0.1em] text-[#137A5A]">RECOMMENDED PLAN</p><p className="mt-1 text-sm font-black">{strategy.title}</p><p className="mt-1 text-xs leading-5 text-[#536159]">{strategy.description || strategy.secondary}</p><p className="mt-2 text-[11px] font-bold text-[#075C45]">검토 채널 · {strategy.channel || "운영자 검토"}</p></div><Link to={item.href} className="mt-4 flex min-h-11 items-center justify-center rounded-lg bg-[#075C45] px-4 text-sm font-black text-white">개인 특별 관리안 설계 계속 →</Link></div></aside>;
}

function PanelMetric({ label, value }) {
  return <div className="min-w-0 border-r border-[#E5EAE6] px-4 py-3 last:border-r-0"><p className="text-[10px] font-bold text-[#718078]">{label}</p><p className="mt-1 truncate text-sm font-black text-[#17211D]">{value || "—"}</p></div>;
}

function EvidenceRow({ label, value }) {
  return <div className="flex items-center justify-between gap-3 px-3 py-3 text-xs"><span className="font-bold text-[#536159]">{label}</span><strong className="text-right text-[#075C45]">{value || "—"}</strong></div>;
}

function RecentPlanTable({ groups }) {
  return <section className="mt-3 overflow-hidden rounded-xl border border-[#DDE4DF] bg-white"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E5EAE6] px-4 py-3"><div><p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">SAVED OPERATION PLANS</p><h2 className="mt-0.5 text-base font-black">최근 저장 운영안</h2></div><Link to="/operations-history?tab=plans" className="rounded-lg border border-[#B7D8C8] px-3 py-2 text-xs font-black text-[#075C45]">운영 결과·알림에서 전체 보기 →</Link></div>{groups.length === 0 ? <p className="px-4 py-8 text-center text-sm font-bold text-[#718078]">아직 저장된 운영안이 없습니다.</p> : <div className="divide-y divide-[#EDF0EE]">{groups.map(({ key, target, count, latest }) => <div key={key} className="grid gap-3 px-4 py-3 text-xs sm:grid-cols-[64px_minmax(140px,1fr)_minmax(140px,1fr)_90px_110px] sm:items-center"><span className="rounded-full bg-[#EEF7F2] px-2 py-1 text-center font-black text-[#075C45]">{latest.planType === "individual" ? "개인" : "지역"}</span><span className="truncate font-black text-[#17211D]">{latest.planType === "individual" ? maskReviewerId(target) : target}</span><span className="truncate text-[#536159]">{latest.actionType || latest.managerDecision || "운영안"}</span><span className="text-[#718078]">버전 {count}건</span><Link to={`/operations-history?tab=plans&planId=${encodeURIComponent(latest.planId)}`} className="font-black text-[#075C45] underline">기록 확인 →</Link></div>)}</div>}</section>;
}

export default PlaybookPage;
