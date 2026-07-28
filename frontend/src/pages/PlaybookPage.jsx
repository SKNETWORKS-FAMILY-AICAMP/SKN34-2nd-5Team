import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";

import DataModeBadge from "../components/DataModeBadge";
import {
  formatTopPercent,
  operationsSummary,
  playbooks,
  reviewers,
  riskTypes,
} from "../data";
import { getDecisionsForModel } from "../services/decisionStorage";

// Which playbook a reviewer falls into before anyone has judged them.
const judgmentToDecision = {
  "유지 우세": "변화 지켜보기",
  "약화 우세": "리뷰 활동 늘리기",
  "중단 우세": "리뷰 다시 시작 유도",
};

const decisionTones = {
  "리뷰 다시 시작 유도": "bg-[#F7E8E5] text-[#E15D47]",
  "리뷰 활동 늘리기": "bg-[#FAEFD9] text-[#A66A18]",
  "변화 지켜보기": "bg-[#E3F1EA] text-[#137A5A]",
  "이번엔 제외": "bg-[#F1F4F1] text-[#68736D]",
};

// Campaign execution has no data behind it yet, so the section stays disabled.
const campaignCapabilities = [
  { title: "대상 배정", description: "담당자별 검토 대상 분배" },
  { title: "접촉 이력", description: "발송 채널과 일자 기록" },
  { title: "복귀 관찰", description: "개입 이후 리뷰 재개 여부" },
  { title: "성과 비교", description: "개입군과 비교군의 활동 차이" },
];

function PlaybookPage() {
  const [searchParams] = useSearchParams();
  const contextUserId = searchParams.get("reviewer");

  const [riskTypeFilter, setRiskTypeFilter] = useState("전체");
  const [decisions] = useState(() =>
    getDecisionsForModel(operationsSummary.modelVersion),
  );

  const reviewersWithDecisions = useMemo(
    () =>
      reviewers.map((reviewer) => ({
        ...reviewer,
        managerDecision: decisions[reviewer.sampleId] ?? null,
        // Undecided reviewers are routed by the model's judgment instead —
        // used to place cards/tables, never as a stand-in for a real decision.
        effectiveDecision:
          decisions[reviewer.sampleId] ??
          judgmentToDecision[reviewer.modelJudgment],
      })),
    [decisions],
  );

  const contextReviewer = contextUserId
    ? reviewersWithDecisions.find(
        (reviewer) => reviewer.userId === contextUserId,
      )
    : null;

  // A. Actual manager judgments only (this browser's decisionStorage), with
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
  }, [contextReviewer]);

  function matchingReviewers(decision) {
    let pool = reviewersWithDecisions.filter(
      (reviewer) => reviewer.effectiveDecision === decision,
    );

    if (riskTypeFilter !== "전체") {
      pool = pool.filter((reviewer) => reviewer.riskType === riskTypeFilter);
    }

    return pool.sort(
      (first, second) => first.priorityRank - second.priorityRank,
    );
  }

  return (
    <section>
      <div className="flex flex-col justify-between gap-5 border-b border-[#DDE4DF] pb-7 lg:flex-row">
        <div>
          <p className="text-xs font-bold tracking-[0.15em] text-[#4C987C]">
            RETENTION PLAYBOOK
          </p>

          <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] text-[#17211D] md:text-5xl">
            판단별 리텐션 플레이북
          </h1>

          <p className="mt-4 max-w-3xl leading-7 text-[#68736D]">
            관리자 판단별로 어떤 조치를 검토할지 정리했습니다. 아직 판단하지
            않은 리뷰어는 모델 판단 기준으로 분류됩니다.
          </p>
        </div>

        <div className="lg:text-right">
          <DataModeBadge />

          <p className="mt-2 text-xs text-[#68736D]">규칙 기반 프로토타입</p>
        </div>
      </div>

      {contextReviewer && (
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

            <span className="rounded bg-white px-2 py-1 text-xs text-[#68736D]">
              {contextReviewer.priorityRank}위 · 상위{" "}
              {formatTopPercent(contextReviewer.priorityTopPercent)}
            </span>

            <span className="rounded bg-white px-2 py-1 text-xs text-[#68736D]">
              {contextReviewer.modelJudgment}
            </span>

            <span className="rounded bg-white px-2 py-1 text-xs text-[#68736D]">
              {contextReviewer.riskType}
            </span>
          </div>

          <p className="mt-3 text-sm text-[#17211D]">
            {contextReviewer.managerDecision
              ? `관리자 판단 "${contextReviewer.managerDecision}" 기준 플레이북을 먼저 표시합니다.`
              : `아직 판단 전이라 모델 판단 기준으로 "${contextReviewer.effectiveDecision}" 플레이북을 먼저 표시합니다.`}
          </p>
        </div>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="text-xl font-bold text-[#17211D]">
            관리자 판단 현황
          </h2>

          <p className="mt-2 text-sm text-[#68736D]">
            이 브라우저에 저장된 실제 판단만 집계합니다 · 전체{" "}
            {reviewersWithDecisions.length.toLocaleString()}명 기준.
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
          <h2 className="text-xl font-bold text-[#17211D]">
            미검토 리뷰어의 모델 기준 추천 경로
          </h2>

          <p className="mt-2 text-sm text-[#68736D]">
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
        <span className="text-xs font-semibold text-[#68736D]">위험 유형</span>

        {["전체", ...riskTypes].map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setRiskTypeFilter(option)}
            className={[
              "rounded-full border px-3 py-1 text-xs font-bold transition",
              riskTypeFilter === option
                ? "border-[#137A5A] bg-[#E3F1EA] text-[#137A5A]"
                : "border-[#DDE4DF] text-[#68736D] hover:border-[#137A5A]",
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
                          decisionTones[playbook.decision] ?? ""
                        }`}
                      >
                        모델 {playbook.modelJudgment}
                      </span>
                    )}
                  </div>

                  <p className="mt-3 max-w-3xl text-sm leading-6 text-[#68736D]">
                    {playbook.condition}
                  </p>
                </div>

                <span className="whitespace-nowrap rounded-full bg-[#F1F4F1] px-3 py-1 text-xs font-bold text-[#68736D]">
                  {pool.length.toLocaleString()}명 해당
                </span>
              </div>

              <p className="mt-2 text-xs text-[#68736D]">
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

              <p className="mt-4 rounded-lg bg-[#F1F4F1] px-4 py-3 text-xs leading-5 text-[#68736D]">
                고도화 필요 · {playbook.needsUpgrade}
              </p>

              {pool.length > 0 && (
                <div className="mt-5">
                  <p className="text-xs font-semibold text-[#68736D]">
                    이 판단에 해당하는 리뷰어 · 상위 10명
                  </p>

                  <div className="mt-3 overflow-x-auto">
                    <table className="min-w-[560px] text-sm">
                      <thead>
                        <tr className="text-left text-xs text-[#68736D]">
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
                            <td className="py-2 pr-4 text-[#68736D]">
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

                            <td className="py-2 pr-4 text-[#68736D]">
                              {reviewer.modelJudgment}
                            </td>

                            <td className="py-2 text-[#68736D]">
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

      <div className="mt-10 rounded-xl border border-[#DDE4DF] bg-white p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-bold text-[#17211D]">
            캠페인 실행과 성과 추적
          </h2>

          <span className="rounded bg-[#F1F4F1] px-2 py-1 text-xs text-[#68736D]">
            고도화 예정
          </span>
        </div>

        <p className="mt-2 text-sm text-[#68736D]">
          개입 이력과 결과를 저장할 데이터가 아직 없어 실행 기능은 비활성
          상태입니다.
        </p>

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          {campaignCapabilities.map((item) => (
            <div key={item.title} className="rounded-xl bg-[#F7F8F5] p-5">
              <div className="flex items-start justify-between gap-3">
                <p className="font-bold text-[#17211D]">{item.title}</p>

                <span className="whitespace-nowrap rounded bg-white px-2 py-1 text-xs text-[#68736D]">
                  정의·데이터 필요
                </span>
              </div>

              <p className="mt-2 text-sm text-[#68736D]">{item.description}</p>
            </div>
          ))}
        </div>

        <fieldset
          disabled
          className="mt-6 grid gap-3 border-t border-[#DDE4DF] pt-5 opacity-60 sm:grid-cols-[1fr_1fr_auto]"
        >
          <input
            type="text"
            placeholder="담당자"
            className="min-h-11 rounded-lg border border-[#DDE4DF] px-3 text-sm"
          />

          <select className="min-h-11 rounded-lg border border-[#DDE4DF] px-3 text-sm">
            <option>채널 선택</option>
          </select>

          <button
            type="button"
            className="min-h-11 rounded-lg bg-[#B8C0BB] px-5 font-bold text-white"
          >
            캠페인 생성
          </button>
        </fieldset>
      </div>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs leading-5 text-[#68736D]">
        이 플레이북은 개입 효과가 검증된 처방이 아니며, 의학적 상태를 의미하지
        않습니다 · Reviewer Retention · {operationsSummary.dataModeLabel} data
      </footer>
    </section>
  );
}

function Row({ label, value }) {
  return (
    <div>
      <p className="text-xs font-semibold text-[#68736D]">{label}</p>
      <p className="mt-1 text-[#17211D]">{value}</p>
    </div>
  );
}

export default PlaybookPage;
