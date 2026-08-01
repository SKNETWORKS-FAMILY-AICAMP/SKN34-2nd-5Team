import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";

import DataModeBadge from "../components/DataModeBadge";
import PageHeader from "../components/common/PageHeader";
import EmptyState from "../components/common/EmptyState";
import ReviewerFilters from "../components/reviewers/ReviewerFilters";
import ReviewerSplitList from "../components/reviewers/ReviewerSplitList";
import ReviewerSplitPanel from "../components/reviewers/ReviewerSplitPanel";
import {
  useOperationsSummary,
  useReviewers,
  useRiskTypes,
} from "../context/operations-context";
import { useDecisions } from "../context/DecisionContext";

const DEFAULT_JUDGMENT = ["약화 우세", "중단 우세"];
const VALID_STATUS = ["전체", "미검토", "검토 완료"];
const VALID_JUDGMENT = ["유지 우세", "약화 우세", "중단 우세"];
const VALID_CRM_RANGE = ["전체", "상위 20%", "상위 20% 제외"];
const VALID_SORT = ["우선순위", "중단 점수", "약화 점수", "활동 감소순", "리뷰 공백"];

// URL search params are the single source of truth for filters (B-6) —
// wrong/unknown values fall back to the same default a fresh visit gets,
// rather than rendering blank or throwing.
function readEnum(searchParams, key, fallback, validValues) {
  const value = searchParams.get(key);
  return value !== null && validValues.includes(value) ? value : fallback;
}

function readJudgment(searchParams) {
  if (!searchParams.has("judgment")) return DEFAULT_JUDGMENT;
  const raw = searchParams.get("judgment");
  if (raw === "") return [];
  return raw.split(",").filter((item) => VALID_JUDGMENT.includes(item));
}

function ReviewerListPage() {
  const operationsSummary = useOperationsSummary();
  const reviewers = useReviewers();
  const riskTypes = useRiskTypes();
  const { decisions } = useDecisions();
  const [searchParams, setSearchParams] = useSearchParams();

  // Filters are read straight from the URL on every render — no component
  // state duplicating them — so a browser back/forward, a reload, or a
  // shared link all restore the same view (B-6). Only ephemeral UI state
  // (visible page size, selection, which row is focused) stays local.
  const searchText = searchParams.get("q") ?? "";
  const statusFilter = readEnum(searchParams, "status", "전체", VALID_STATUS);
  const judgmentFilters = readJudgment(searchParams);
  const riskTypeFilter = searchParams.get("riskType") ?? "전체";
  const crmRangeFilter = readEnum(searchParams, "crm", "전체", VALID_CRM_RANGE);
  const sortRule = readEnum(searchParams, "sort", "우선순위", VALID_SORT);

  const recencyMin = searchParams.has("recencyMin")
    ? Number(searchParams.get("recencyMin"))
    : null;
  const recencyMaxRaw = searchParams.get("recencyMax");
  const recencyMax =
    recencyMaxRaw === "" || recencyMaxRaw === null
      ? Infinity
      : Number(recencyMaxRaw);
  const activeMonthsParam = searchParams.has("activeMonths")
    ? Number(searchParams.get("activeMonths"))
    : null;

  const [visibleCount, setVisibleCount] = useState(100);
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [activeReviewerId, setActiveReviewerId] = useState(null);

  // Merges one field into the URL, dropping keys back to "absent" when
  // they're set to that filter's default so the URL stays short for the
  // common case instead of always carrying every param.
  const setFilter = useCallback(
    (key, value, { isDefault } = {}) => {
      setVisibleCount(100);
      setSearchParams(
        (previous) => {
          const next = new URLSearchParams(previous);
          if (isDefault?.(value)) {
            next.delete(key);
          } else {
            next.set(key, value);
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  function clearAtlasFilter() {
    setSearchParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        next.delete("recencyMin");
        next.delete("recencyMax");
        next.delete("activeMonths");
        return next;
      },
      { replace: true },
    );
  }

  function resetAllFilters() {
    setVisibleCount(100);
    setSearchParams(new URLSearchParams(), { replace: true });
  }

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

  const pendingCount = reviewersWithDecisions.length - completedCount;

  const completedTargetCount = reviewersWithDecisions.filter(
    (reviewer) => reviewer.crmTarget && reviewer.managerDecision,
  ).length;
  const targetProgress =
    operationsSummary.targetUsers > 0
      ? completedTargetCount / operationsSummary.targetUsers
      : 0;

  const filteredReviewers = useMemo(() => {
    let result = [...reviewersWithDecisions];

    if (searchText.trim()) {
      result = result.filter((reviewer) =>
        reviewer.userId
          .toLowerCase()
          .includes(searchText.trim().toLowerCase()),
      );
    }

    if (statusFilter === "미검토") {
      result = result.filter((reviewer) => !reviewer.managerDecision);
    }

    if (statusFilter === "검토 완료") {
      result = result.filter((reviewer) => reviewer.managerDecision);
    }

    if (judgmentFilters.length > 0) {
      result = result.filter((reviewer) =>
        judgmentFilters.includes(reviewer.modelJudgment),
      );
    }

    if (riskTypeFilter !== "전체") {
      result = result.filter(
        (reviewer) => reviewer.riskType === riskTypeFilter,
      );
    }

    if (crmRangeFilter === "상위 20%") {
      result = result.filter((reviewer) => reviewer.crmTarget);
    } else if (crmRangeFilter === "상위 20% 제외") {
      result = result.filter((reviewer) => !reviewer.crmTarget);
    }

    if (recencyMin !== null) {
      result = result.filter(
        (reviewer) =>
          reviewer.recentRecencyDays >= recencyMin &&
          reviewer.recentRecencyDays < recencyMax,
      );
    }

    if (activeMonthsParam !== null) {
      result = result.filter(
        (reviewer) => reviewer.recentActiveMonths === activeMonthsParam,
      );
    }

    if (sortRule === "중단 점수") {
      result.sort(
        (first, second) => second.scores.stopped - first.scores.stopped,
      );
    } else if (sortRule === "약화 점수") {
      result.sort(
        (first, second) => second.scores.weakened - first.scores.weakened,
      );
    } else if (sortRule === "활동 감소순") {
      result.sort(
        (first, second) =>
          second.activeMonthDeclineRate - first.activeMonthDeclineRate,
      );
    } else if (sortRule === "리뷰 공백") {
      result.sort(
        (first, second) =>
          second.recentRecencyDays - first.recentRecencyDays,
      );
    } else {
      result.sort(
        (first, second) => first.priorityRank - second.priorityRank,
      );
    }

    return result;
  }, [
    searchText,
    statusFilter,
    judgmentFilters,
    riskTypeFilter,
    crmRangeFilter,
    sortRule,
    recencyMin,
    recencyMax,
    activeMonthsParam,
    reviewersWithDecisions,
  ]);

  const visibleReviewers = filteredReviewers.slice(0, visibleCount);
  const remainingCount = filteredReviewers.length - visibleReviewers.length;

  // Derived during render instead of synced via effect+setState: falls
  // back to the first visible row whenever the selected id isn't in the
  // current filtered/paginated set (nothing selected yet, or a filter
  // change dropped the previous selection).
  const activeReviewer =
    visibleReviewers.find((reviewer) => reviewer.userId === activeReviewerId) ??
    visibleReviewers[0];

  useEffect(() => {
    function onKeyDown(event) {
      const tag = document.activeElement?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (event.key !== "j" && event.key !== "k") return;

      const index = visibleReviewers.findIndex(
        (reviewer) => reviewer.userId === activeReviewerId,
      );
      const nextIndex =
        event.key === "j"
          ? Math.min(index + 1, visibleReviewers.length - 1)
          : Math.max(index - 1, 0);

      if (visibleReviewers[nextIndex]) {
        setActiveReviewerId(visibleReviewers[nextIndex].userId);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [visibleReviewers, activeReviewerId]);

  function advanceToNextUnreviewed(currentUserId) {
    const pending = visibleReviewers.filter(
      (reviewer) =>
        reviewer.userId !== currentUserId && !reviewer.managerDecision,
    );
    if (pending.length > 0) {
      setActiveReviewerId(pending[0].userId);
    }
  }

  function toggleSelect(userId) {
    setSelectedIds((previous) => {
      const next = new Set(previous);
      if (next.has(userId)) next.delete(userId);
      else next.add(userId);
      return next;
    });
  }

  function toggleSelectAll(ids) {
    setSelectedIds((previous) => {
      const allSelected = ids.every((id) => previous.has(id));
      if (allSelected) return new Set();
      return new Set(ids);
    });
  }

  function downloadCsv(rows, filename) {
    const header = [
      "priority_rank",
      "user_id",
      "model_judgment",
      "risk_type",
      "core_change",
      "recommended_review",
      "manager_decision",
    ];

    const csvRows = rows.map((reviewer) => [
      reviewer.priorityRank,
      reviewer.userId,
      reviewer.modelJudgment,
      reviewer.riskType,
      reviewer.coreChange,
      reviewer.recommendedReview,
      reviewer.managerDecision ?? "",
    ]);

    const csvContent = [header, ...csvRows]
      .map((row) =>
        row
          .map((value) => `"${String(value).replaceAll('"', '""')}"`)
          .join(","),
      )
      .join("\n");

    const bom = String.fromCharCode(0xfeff);
    const blob = new Blob([bom + csvContent], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  const selectedReviewers = filteredReviewers.filter((reviewer) =>
    selectedIds.has(reviewer.userId),
  );

  return (
    <section>
      <PageHeader
        title="리뷰어 검토"
        meta={<DataModeBadge />}
      >
        <div className="flex flex-wrap gap-x-2 gap-y-1 text-xs text-[#626D67]">
          <span>전체 {reviewersWithDecisions.length.toLocaleString()}</span>
          <span>·</span>
          <span>미검토 {pendingCount.toLocaleString()}</span>
          <span>·</span>
          <span className="text-[#137A5A]">완료 {completedCount.toLocaleString()}</span>
        </div>
      </PageHeader>

      <div className="mt-3 flex items-center gap-3 rounded-lg border border-[#DDE4DF] bg-white px-4 py-2.5">
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

      {(recencyMin !== null || activeMonthsParam !== null) && (
        <div className="mt-3 flex items-center gap-2 rounded-lg bg-[#E3F1EA] px-3 py-2 text-xs text-[#137A5A]">
          <span>
            Signal Atlas에서 이동함
            {activeMonthsParam !== null && ` · 활동 ${activeMonthsParam}개월`}
            {recencyMin !== null &&
              ` · 경과 ${recencyMin}~${Number.isFinite(recencyMax) ? recencyMax : "∞"}일`}
          </span>
          <button
            type="button"
            onClick={clearAtlasFilter}
            className="ml-auto font-medium underline"
          >
            필터 해제
          </button>
        </div>
      )}

      <div className="mt-3">
        <ReviewerFilters
          searchText={searchText}
          onSearchChange={(value) =>
            setFilter("q", value, { isDefault: (v) => v === "" })
          }
          statusFilter={statusFilter}
          onStatusChange={(value) =>
            setFilter("status", value, { isDefault: (v) => v === "전체" })
          }
          judgmentFilters={judgmentFilters}
          onJudgmentFiltersChange={(value) => {
            const isDefaultSet =
              value.length === DEFAULT_JUDGMENT.length &&
              [...value].sort().join() === [...DEFAULT_JUDGMENT].sort().join();
            setFilter("judgment", value.join(","), {
              isDefault: () => isDefaultSet,
            });
          }}
          riskTypeFilter={riskTypeFilter}
          onRiskTypeChange={(value) =>
            setFilter("riskType", value, { isDefault: (v) => v === "전체" })
          }
          crmRangeFilter={crmRangeFilter}
          onCrmRangeChange={(value) =>
            setFilter("crm", value, { isDefault: (v) => v === "전체" })
          }
          sortRule={sortRule}
          onSortChange={(value) =>
            setFilter("sort", value, { isDefault: (v) => v === "우선순위" })
          }
          riskTypes={riskTypes}
        />
      </div>

      <div className="mt-3 flex justify-end">
        <button
          type="button"
          onClick={() => downloadCsv(filteredReviewers, "reviewer_worklist.csv")}
          className="min-h-8 rounded-lg border border-[#DDE4DF] px-3 text-xs font-medium text-[#626D67] transition hover:border-[#137A5A] hover:text-[#137A5A]"
        >
          CSV 다운로드
        </button>
      </div>

      {visibleReviewers.length === 0 ? (
        <div className="mt-4">
          <EmptyState
            title="조건에 맞는 리뷰어가 없습니다"
            description="검색어나 필터 조건을 바꿔 보세요."
            actionLabel="필터 초기화"
            onAction={resetAllFilters}
          />
        </div>
      ) : (
        <div className="mt-4 grid gap-4 xl:grid-cols-[1.8fr_1fr]">
          <div>
            <ReviewerSplitList
              reviewers={visibleReviewers}
              activeReviewerId={activeReviewerId}
              onSelect={(reviewer) => setActiveReviewerId(reviewer.userId)}
              selectedIds={selectedIds}
              onToggleSelect={toggleSelect}
              onToggleSelectAll={toggleSelectAll}
            />

            {selectedIds.size > 0 && (
              <div className="mt-2 flex flex-wrap items-center gap-2 rounded-lg bg-[#17211D] px-3 py-2.5 text-xs text-white">
                <span className="font-medium">
                  {selectedIds.size}명 선택됨
                </span>
                <span
                  className="text-[10px] text-[#B3BBB6]"
                  title="관리자 판단은 근거를 개별로 확인한 뒤 리뷰어 상세에서만 저장합니다"
                >
                  관리적 액션만 일괄 가능 ⓘ
                </span>
                <button
                  type="button"
                  disabled
                  title="담당자 DB 연동 후 활성화됩니다"
                  className="min-h-7 cursor-not-allowed rounded bg-[#2B362F] px-2.5 text-[11px] opacity-50"
                >
                  담당자 배정
                </button>
                <button
                  type="button"
                  disabled
                  title="대상 명단 DB 연동 후 활성화됩니다"
                  className="min-h-7 cursor-not-allowed rounded bg-[#2B362F] px-2.5 text-[11px] opacity-50"
                >
                  대상 명단에 추가
                </button>
                <button
                  type="button"
                  disabled
                  title="스누즈 DB 연동 후 활성화됩니다"
                  className="min-h-7 cursor-not-allowed rounded bg-[#2B362F] px-2.5 text-[11px] opacity-50"
                >
                  스누즈
                </button>
                <button
                  type="button"
                  onClick={() =>
                    downloadCsv(selectedReviewers, "reviewer_selection.csv")
                  }
                  className="min-h-7 rounded bg-[#137A5A] px-2.5 text-[11px] font-medium"
                >
                  CSV로 내보내기
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedIds(new Set())}
                  className="ml-auto text-[11px] text-[#B3BBB6]"
                >
                  선택 해제
                </button>
              </div>
            )}

            <p className="mt-3 text-xs text-[#626D67]">
              전체 {operationsSummary.totalReviewers.toLocaleString()}명 · 조건에
              맞는 {filteredReviewers.length.toLocaleString()}명 중{" "}
              {visibleReviewers.length.toLocaleString()}명 표시
            </p>

            {remainingCount > 0 && (
              <button
                type="button"
                onClick={() => setVisibleCount((count) => count + 100)}
                className="mt-2 min-h-9 rounded-lg border border-[#137A5A] px-4 text-xs font-medium text-[#137A5A] transition hover:bg-[#E3F1EA]"
              >
                다음 {Math.min(100, remainingCount)}명 불러오기 (100명 단위)
              </button>
            )}
          </div>

          <div>
            {activeReviewer ? (
              <ReviewerSplitPanel
                key={activeReviewer.userId}
                reviewer={activeReviewer}
                onAdvance={advanceToNextUnreviewed}
              />
            ) : (
              <EmptyState title="왼쪽에서 리뷰어를 선택하세요" />
            )}
          </div>
        </div>
      )}

      <footer className="mt-10 border-t border-[#DDE4DF] pt-4 text-xs text-[#626D67]">
        {operationsSummary.modelVersion} 실데이터 · 전체 코호트{" "}
        {reviewersWithDecisions.length.toLocaleString()}명 · 숫자키 1~4로 판단
        선택, J/K로 이동
      </footer>
    </section>
  );
}

export default ReviewerListPage;
