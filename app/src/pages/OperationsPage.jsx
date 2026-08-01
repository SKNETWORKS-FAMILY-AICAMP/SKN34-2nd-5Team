import { useMemo } from "react";
import { Link } from "react-router";

import DataModeBadge from "../components/DataModeBadge";
import PageHeader from "../components/common/PageHeader";
import PolicyPanel from "../components/operations/PolicyPanel";
import PriorityQueue from "../components/operations/PriorityQueue";
import SignalAtlas from "../components/operations/SignalAtlas";
import { useOperationsSummary, useReviewers } from "../context/operations-context";
import { useDecisions } from "../context/DecisionContext";

function OperationsPage() {
  const operationsSummary = useOperationsSummary();
  const reviewers = useReviewers();
  const { decisions } = useDecisions();

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

  return (
    <section>
      <PageHeader
        title="운영 홈"
        meta={
          <>
            <DataModeBadge />
            <p className="mt-2 text-xs text-[#626D67]">
              {operationsSummary.targetYear}년 실제 상태 검증 스냅샷
            </p>
          </>
        }
      >
        <div className="flex flex-wrap gap-x-2 gap-y-1 text-xs text-[#626D67]">
          <span>전체 {operationsSummary.totalReviewers.toLocaleString()}</span>
          <span>·</span>
          <span>검토 대상 {operationsSummary.targetUsers.toLocaleString()}</span>
          <span>·</span>
          <span className="text-[#137A5A]">
            판단 완료 {completedCount.toLocaleString()} · 서버 저장 기준
          </span>
        </div>
      </PageHeader>

      <div className="mt-4 flex items-center gap-3 rounded-lg border border-[#DDE4DF] bg-white px-4 py-2.5">
        <span className="shrink-0 text-xs text-[#626D67]">오늘 진행률</span>
        <div className="h-2 flex-1 rounded-full bg-[#F1F4F1]">
          <div
            className="h-2 rounded-full bg-[#137A5A] transition-all"
            style={{ width: `${Math.min(100, targetProgress * 100)}%` }}
          />
        </div>
        <span className="shrink-0 text-xs font-medium text-[#17211D]">
          검토 대상 {operationsSummary.targetUsers.toLocaleString()}명 중{" "}
          {completedTargetCount.toLocaleString()}명 처리
        </span>
      </div>

      <div className="mt-5 grid items-start gap-5 xl:grid-cols-[1.5fr_1fr]">
        <SignalAtlas reviewers={reviewers} />

        <div>
          <div className="flex items-baseline justify-between">
            <p className="text-sm font-medium text-[#17211D]">
              오늘 먼저 볼 {priorityReviewers.length}명
            </p>
            <span className="text-xs text-[#626D67]">판단 완료 제외</span>
          </div>

          <div className="mt-2">
            <PriorityQueue reviewers={priorityReviewers} />
          </div>

          <div className="mt-3 flex gap-2">
            <Link
              to={priorityReviewers[0] ? `/reviewers/${priorityReviewers[0].userId}` : "/reviewers"}
              className="flex min-h-9 flex-1 items-center justify-center rounded-lg bg-[#137A5A] px-4 text-xs font-medium text-white transition hover:bg-[#185C46]"
            >
              1번부터 검토 시작
            </Link>

            <Link
              to="/reviewers"
              className="flex min-h-9 items-center justify-center rounded-lg border border-[#DDE4DF] px-4 text-xs font-medium text-[#137A5A] transition hover:border-[#137A5A] hover:bg-[#E3F1EA]"
            >
              전체 목록
            </Link>
          </div>

          <p className="mt-2.5 text-[11px] text-[#626D67]">
            판단은 로그인 운영자 이력과 함께 서버에 저장됩니다
          </p>

          <div className="mt-5">
            <PolicyPanel summary={operationsSummary} />
          </div>
        </div>
      </div>

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

export default OperationsPage;
