import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";

import DataModeBadge from "../components/DataModeBadge";
import PageHeader from "../components/common/PageHeader";
import Skeleton from "../components/common/Skeleton";
import ErrorState from "../components/common/ErrorState";
import {
  useOperationsSummary,
  useReviewers,
  useRiskTypes,
} from "../context/OperationsContext";
import { useDecisions } from "../context/DecisionContext";
import {
  formatTopPercent,
  loadPlaybooks,
  loadReviewerRecommendations,
} from "../data";
import {
  createTargetList,
  deleteTargetList,
  loadTargetLists,
} from "../services/targetListService";

// Which playbook a reviewer falls into before anyone has judged them.
const judgmentToDecision = {
  "유지 우세": "변화 지켜보기",
  "약화 우세": "리뷰 활동 늘리기",
  "중단 우세": "리뷰 다시 시작 유도",
};

const decisionTones = {
  "리뷰 다시 시작 유도": "bg-[#F7E8E5] text-[#BF3620]",
  "리뷰 활동 늘리기": "bg-[#FAEFD9] text-[#A66A18]",
  "변화 지켜보기": "bg-[#E3F1EA] text-[#137A5A]",
  "이번엔 제외": "bg-[#F1F4F1] text-[#626D67]",
};

function PlaybookPage() {
  const operationsSummary = useOperationsSummary();
  const reviewers = useReviewers();
  const riskTypes = useRiskTypes();
  const { decisions } = useDecisions();
  const [searchParams] = useSearchParams();
  const contextUserId = searchParams.get("reviewer");

  const [riskTypeFilter, setRiskTypeFilter] = useState("전체");
  const [targetLists, setTargetLists] = useState([]);
  const [listNameDraft, setListNameDraft] = useState("");
  const [listFeedback, setListFeedback] = useState("");
  const [listFeedbackTone, setListFeedbackTone] = useState("success");

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

  if (loadStatus === "error") {
    return <ErrorState message={loadError} />;
  }

  if (loadStatus === "loading") {
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
    } catch (error) {
      setListFeedbackTone("error");
      setListFeedback(error.message);
    }
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

    return pool.sort(
      (first, second) => first.priorityRank - second.priorityRank,
    );
  }

  return (
    <section>
      <PageHeader
        title="리텐션 플레이북"
        description="관리자 판단별로 어떤 조치를 검토할지 정리했습니다. 아직 판단하지 않은 리뷰어는 모델 판단 기준으로 분류됩니다."
        meta={<DataModeBadge />}
      />

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
                          decisionTones[playbook.decision] ?? ""
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
                    className="min-h-8 rounded-lg border border-[#DDE4DF] px-3 text-xs font-medium text-[#137A5A] transition hover:border-[#137A5A] hover:bg-[#E3F1EA]"
                  >
                    CSV 내보내기
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDeleteTargetList(list.listId)}
                    className="min-h-8 rounded-lg border border-[#DDE4DF] px-3 text-xs font-medium text-[#626D67] transition hover:border-[#8A3B2E] hover:text-[#8A3B2E]"
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

function Row({ label, value }) {
  return (
    <div>
      <p className="text-xs font-semibold text-[#626D67]">{label}</p>
      <p className="mt-1 text-[#17211D]">{value}</p>
    </div>
  );
}

export default PlaybookPage;
