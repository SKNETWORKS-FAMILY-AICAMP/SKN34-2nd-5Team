import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";

import DataModeBadge from "../components/DataModeBadge";
import PolicyPanel from "../components/operations/PolicyPanel";
import PriorityQueue from "../components/operations/PriorityQueue";
import SignalAtlas from "../components/operations/SignalAtlas";
import WorkflowContextBar from "../components/workflow/WorkflowContextBar";
import WorkflowHeader from "../components/workflow/WorkflowHeader";
import { useOperationsSummary, useReviewers } from "../context/operations-context";
import { useDecisions } from "../context/DecisionContext";
import { loadRegionalDerivedContext, loadRegionalRisk } from "../data";

const INDIVIDUAL_QUEUE_HREF = "/reviewers?mode=individual&status=미검토&sort=우선순위";

function OperationsPage({ mode = "regional" }) {
  const operationsSummary = useOperationsSummary();
  const reviewers = useReviewers();
  const { decisions } = useDecisions();
  const [regionalRisk, setRegionalRisk] = useState(null);
  const [regionalDerived, setRegionalDerived] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([loadRegionalRisk(), loadRegionalDerivedContext()])
      .then(([risk, derived]) => {
        if (cancelled) return;
        setRegionalRisk(risk);
        setRegionalDerived(derived.available ? derived : null);
      })
      .catch(() => {
        // The home remains usable when the optional regional context is unavailable.
      });
    return () => { cancelled = true; };
  }, []);

  const reviewersWithDecisions = useMemo(
    () =>
      reviewers.map((reviewer) => ({
        ...reviewer,
        managerDecision: decisions[reviewer.userId]?.decision ?? null,
      })),
    [decisions, reviewers],
  );

  const completedCount = reviewersWithDecisions.filter(
    (reviewer) => reviewer.managerDecision,
  ).length;

  // Progress against the actual review queue (crmTarget population), not
  // the full 6,533-person cohort — completedCount above counts decisions
  // anywhere, but "오늘 처리할 일"은 검토 대상 1,307명 기준입니다.
  const completedTargetCount = reviewersWithDecisions.filter(
    (reviewer) => reviewer.crmTarget && reviewer.managerDecision,
  ).length;
  const targetProgress =
    operationsSummary.targetUsers > 0
      ? completedTargetCount / operationsSummary.targetUsers
      : 0;

  const priorityReviewers = useMemo(
    () =>
      reviewersWithDecisions
        .filter((reviewer) => !reviewer.managerDecision)
        .sort((first, second) => first.priorityRank - second.priorityRank)
        .slice(0, 5)
        .map((reviewer) => ({
          rank: reviewer.priorityRank,
          userId: reviewer.userId,
          modelJudgment: reviewer.modelJudgment,
          changeText: reviewer.coreChange,
          action: reviewer.recommendedReview,
        })),
    [reviewersWithDecisions],
  );

  const regionalBrief = useMemo(() => {
    if (!regionalRisk || !regionalDerived) return null;
    const byRegion = new Map(regionalRisk.regions.map((region) => [region.region, region]));
    return regionalDerived.regions
      .filter((region) => region.reviewSupplyChangeRate !== null)
      .map((region) => ({ ...region, ...byRegion.get(region.region) }))
      .sort((first, second) => first.reviewSupplyChangeRate - second.reviewSupplyChangeRate)[0] ?? null;
  }, [regionalDerived, regionalRisk]);

  const regionalShortlist = useMemo(() => {
    if (!regionalRisk || !regionalDerived) return [];
    const byRegion = new Map(regionalRisk.regions.map((region) => [region.region, region]));
    return regionalDerived.regions
      .filter((region) => region.reviewSupplyChangeRate !== null)
      .map((region) => ({ ...region, ...byRegion.get(region.region) }))
      .sort((first, second) => first.reviewSupplyChangeRate - second.reviewSupplyChangeRate)
      .slice(0, 4);
  }, [regionalDerived, regionalRisk]);

  return (
    <section className="pb-5">
      <WorkflowHeader
        eyebrow={mode === "regional" ? "REGIONAL OPERATIONS" : "INDIVIDUAL OPERATIONS"}
        title={mode === "regional" ? "권역 운영 홈" : "개인 운영 홈"}
        description={mode === "regional" ? "리뷰 공급 변화를 기준으로 우선 확인 권역을 찾고, 대상 검토에서 콘텐츠 캠페인 저장까지 이어갑니다." : "우선순위 큐에서 리뷰어를 선택하고, 활동 근거 검토부터 관리자 판단과 개인 개입안 저장까지 이어갑니다."}
        steps={["운영 신호 확인", "대상 선정", "근거 검토·판단", "운영안 설계", "실행·성과 추적"]}
        activeStep={0}
        aside={<div className="text-right"><DataModeBadge /><p className="mt-2 text-[11px] text-[#718078]">{operationsSummary.targetYear}년 검증 스냅샷</p></div>}
      />

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {mode === "regional" ? (
          <>
            <MetricCard label="분석 권역" value={regionalDerived ? `${regionalDerived.regions.length.toLocaleString()}개` : "—"} note="파생 집계 기준" />
            <MetricCard label="우선 확인 권역" value={regionalBrief?.region ?? "—"} note={regionalBrief?.topCity ?? "권역 데이터 확인 중"} />
            <MetricCard label="CRM 후보" value={regionalBrief ? `${regionalBrief.crmTargets.toLocaleString()}명` : "—"} note="우선 권역 기준" tone="green" />
            <MetricCard label="신규 유입" value={regionalBrief?.newPowerReviewers != null ? `${regionalBrief.newPowerReviewers.toLocaleString()}명` : "—"} note="우선 권역 기준" tone="green" />
          </>
        ) : (
          <>
            <MetricCard label="전체 리뷰어" value={`${operationsSummary.totalReviewers.toLocaleString()}명`} note="분석 코호트" />
            <MetricCard label="검토 대상" value={`${operationsSummary.targetUsers.toLocaleString()}명`} note="CRM 운영 큐" />
            <MetricCard label="판단 완료" value={`${completedCount.toLocaleString()}명`} note="서버 저장 기준" tone="green" />
            <MetricCard label="오늘 진행률" value={`${completedTargetCount.toLocaleString()} / ${operationsSummary.targetUsers.toLocaleString()}`} note={`${(targetProgress * 100).toFixed(1)}% 처리`} tone="green" />
          </>
        )}
      </div>

      {mode === "regional" ? (
        <div className="mt-6">
          <WorkflowContextBar
            label="오늘 먼저 볼 권역"
            title={regionalBrief ? `${regionalBrief.region} · ${regionalBrief.topCity}` : "권역 데이터를 불러오는 중"}
            metrics={regionalBrief ? [
              { label: "리뷰 공급", value: `${regionalBrief.reviewSupplyChangeRate >= 0 ? "+" : ""}${(regionalBrief.reviewSupplyChangeRate * 100).toFixed(1)}%` },
              { label: "CRM 후보", value: `${regionalBrief.crmTargets.toLocaleString()}명` },
              { label: "기준", value: "전년 대비" },
            ] : []}
            action={<Link to={regionalBrief ? `/regional?region=${encodeURIComponent(regionalBrief.region)}` : "/regional"} className="inline-flex min-h-10 items-center rounded-lg bg-[#075C45] px-4 text-xs font-bold text-white hover:bg-[#064936]">권역 지도에서 확인</Link>}
          />

          <div className="mt-4 grid items-start gap-5 xl:grid-cols-[1.35fr_0.65fr]">
            <section className="overflow-hidden rounded-2xl border border-[#DDE4DF] bg-white">
              <div className="flex items-start justify-between gap-4 border-b border-[#E5EAE6] px-6 py-5">
                <div><p className="text-xs font-black tracking-[0.1em] text-[#137A5A]">REGION WATCH</p><h2 className="mt-1 text-lg font-black">콘텐츠 공급 우선 확인 권역</h2><p className="mt-1 text-xs text-[#626D67]">실제 감소뿐 아니라 전체 권역 대비 상대적 둔화도 함께 검토합니다.</p></div>
                <Link to="/regional" className="shrink-0 text-xs font-bold text-[#137A5A] underline">전체 권역 보기</Link>
              </div>
              <div className="divide-y divide-[#EDF0EE]">
                {regionalShortlist.length > 0 ? regionalShortlist.map((region, index) => (
                  <Link key={region.region} to={`/regional?region=${encodeURIComponent(region.region)}`} className="grid min-h-16 grid-cols-[40px_minmax(0,1fr)_110px_100px] items-center gap-3 px-6 hover:bg-[#F7FAF8]">
                    <span className="grid h-7 w-7 place-items-center rounded-full bg-[#EEF4F0] text-xs font-black text-[#075C45]">{index + 1}</span>
                    <span className="min-w-0"><strong className="block truncate text-sm">{region.region} · {region.topCity}</strong><span className="text-xs text-[#718078]">CRM 후보 {region.crmTargets.toLocaleString()}명</span></span>
                    <span className="h-2 overflow-hidden rounded-full bg-[#EEF1EF]"><span className={`block h-full rounded-full ${region.reviewSupplyChangeRate < 0 ? "bg-[#E15D47]" : "bg-[#8FB9A5]"}`} style={{ width: `${Math.min(100, Math.max(12, Math.abs(region.reviewSupplyChangeRate) * 500))}%` }} /></span>
                    <strong className={region.reviewSupplyChangeRate < 0 ? "text-right text-sm text-[#C94734]" : "text-right text-sm text-[#137A5A]"}>{region.reviewSupplyChangeRate >= 0 ? "+" : ""}{(region.reviewSupplyChangeRate * 100).toFixed(1)}%</strong>
                  </Link>
                )) : <p className="px-6 py-10 text-center text-sm text-[#718078]">권역 공급 데이터를 불러오는 중입니다.</p>}
              </div>
            </section>

            <aside className="rounded-2xl border border-[#B7D8C8] bg-[#F0F7F3] p-6">
              <p className="text-xs font-black tracking-[0.1em] text-[#137A5A]">NEXT ACTION</p>
              <h2 className="mt-2 text-xl font-black">권역에서 캠페인까지</h2>
              <ol className="mt-5 space-y-4">
                {["지도에서 공급 둔화 권역 확인", "CRM 후보 리뷰어 검토", "음식점·콘텐츠 후보 선택", "30·60·90일 검증 계획 저장"].map((item, index) => <li key={item} className="flex gap-3 text-sm text-[#4B665B]"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-white text-xs font-black text-[#075C45]">{index + 1}</span><span className="pt-0.5">{item}</span></li>)}
              </ol>
              <Link to={regionalBrief ? `/regional?region=${encodeURIComponent(regionalBrief.region)}` : "/regional"} className="mt-6 flex min-h-11 items-center justify-center rounded-xl bg-[#075C45] px-5 text-sm font-black text-white hover:bg-[#064936]">권역 검토 시작</Link>
            </aside>
          </div>
        </div>
      ) : (
        <div className="mt-6">
          <WorkflowContextBar
            label="오늘의 최우선 검토"
            title={priorityReviewers[0]?.userId ?? "검토 대상을 계산하는 중"}
            metrics={priorityReviewers[0] ? [{ label: "우선순위", value: `${priorityReviewers[0].rank}위` }, { label: "모델 판단", value: priorityReviewers[0].modelJudgment }, { label: "상태", value: "관리자 미검토" }] : []}
            action={<Link to={priorityReviewers[0] ? `/reviewers/${priorityReviewers[0].userId}` : INDIVIDUAL_QUEUE_HREF} className="inline-flex min-h-10 items-center rounded-lg bg-[#075C45] px-4 text-xs font-bold text-white hover:bg-[#064936]">Reviewer 360 열기</Link>}
          />

          <div className="mt-4 grid items-start gap-5 xl:grid-cols-[1.35fr_0.65fr]">
            <SignalAtlas reviewers={reviewers} />
            <div>
              <section className="rounded-2xl border border-[#DDE4DF] bg-white p-5">
                <div className="flex items-baseline justify-between"><h2 className="text-sm font-black">오늘 먼저 볼 {priorityReviewers.length}명</h2><span className="text-[11px] text-[#718078]">판단 완료 제외</span></div>
                <div className="mt-3"><PriorityQueue reviewers={priorityReviewers} /></div>
                <div className="mt-4 grid grid-cols-2 gap-2">
                  <Link to={priorityReviewers[0] ? `/reviewers/${priorityReviewers[0].userId}` : INDIVIDUAL_QUEUE_HREF} className="flex min-h-10 items-center justify-center rounded-lg bg-[#075C45] px-3 text-xs font-bold text-white">1번부터 검토</Link>
                  <Link to={INDIVIDUAL_QUEUE_HREF} className="flex min-h-10 items-center justify-center rounded-lg border border-[#B7D8C8] px-3 text-xs font-bold text-[#075C45]">전체 검토 큐</Link>
                </div>
                <p className="mt-3 text-[11px] text-[#718078]">판단은 로그인 운영자 이력과 함께 서버에 저장됩니다.</p>
              </section>
              <div className="mt-5"><PolicyPanel summary={operationsSummary} /></div>
            </div>
          </div>
        </div>
      )}

      <footer className="mt-10 border-t border-[#DDE4DF] pt-4 text-xs text-[#626D67]">
        <p>
          Reviewer Retention · {operationsSummary.dataModeLabel} data · 클래스
          점수는 보정 확률이 아니며 통합 점수는 운영 우선순위에 사용합니다.
        </p>

        <p className="mt-2">
          © 2026 SKN34-2nd-5Team (SK Networks Family AI 캠프) · Yelp Open
          Dataset 기반 비상업 분석
        </p>
      </footer>
    </section>
  );
}

function MetricCard({ label, value, note, tone }) {
  return (
    <article className="rounded-xl border border-[#DDE4DF] bg-white px-5 py-4">
      <p className="text-xs font-semibold text-[#718078]">{label}</p>
      <p className={`mt-1 text-xl font-black ${tone === "green" ? "text-[#075C45]" : "text-[#17211D]"}`}>{value}</p>
      <p className="mt-1 text-[11px] text-[#8A948F]">{note}</p>
    </article>
  );
}

export default OperationsPage;
