import { useMemo, useState } from "react";
import { getDecisionsForModel } from "../services/decisionStorage";
import DataModeBadge from "../components/DataModeBadge";
import ReviewerFilters from "../components/reviewers/ReviewerFilters";
import ReviewerTable from "../components/reviewers/ReviewerTable";
import {
  useOperationsSummary,
  useReviewers,
  useRiskTypes,
} from "../context/operations-context";

function ReviewerListPage() {
  const operationsSummary = useOperationsSummary();
  const reviewers = useReviewers();
  const riskTypes = useRiskTypes();
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState("전체");
  const [judgmentFilters, setJudgmentFilters] = useState([
    "약화 우세",
    "중단 우세",
  ]);
  const [riskTypeFilter, setRiskTypeFilter] = useState("전체");
  const [crmRangeFilter, setCrmRangeFilter] = useState("전체");
  const [sortRule, setSortRule] = useState("우선순위");
  const [visibleCount, setVisibleCount] = useState(100);
  const [decisions] = useState(() =>
    getDecisionsForModel(operationsSummary.modelVersion),
  );

  const reviewersWithDecisions = useMemo(
    () =>
      reviewers.map((reviewer) => ({
        ...reviewer,
        managerDecision: decisions[reviewer.sampleId] ?? null,
      })),
    [decisions, reviewers],
  );

  const completedCount = reviewersWithDecisions.filter(
    (reviewer) => reviewer.managerDecision,
  ).length;

  const pendingCount = reviewersWithDecisions.length - completedCount;

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
        (first, second) =>
          first.priorityRank - second.priorityRank,
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
    reviewersWithDecisions,
  ]);

  function handleDownloadCsv() {
    const header = [
      "priority_rank",
      "user_id",
      "model_judgment",
      "risk_type",
      "core_change",
      "recommended_review",
      "manager_decision",
    ];

    const rows = filteredReviewers.map((reviewer) => [
      reviewer.priorityRank,
      reviewer.userId,
      reviewer.modelJudgment,
      reviewer.riskType,
      reviewer.coreChange,
      reviewer.recommendedReview,
      reviewer.managerDecision ?? "",
    ]);

    const csvContent = [header, ...rows]
      .map((row) =>
        row
          .map((value) => `"${String(value).replaceAll('"', '""')}"`)
          .join(","),
      )
      .join("\n");

    // Excel needs the BOM to read the Korean columns as UTF-8.
    const blob = new Blob([`\ufeff${csvContent}`], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "reviewer_worklist.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  const visibleReviewers = filteredReviewers.slice(0, visibleCount);
  const remainingCount =
    filteredReviewers.length - visibleReviewers.length;

  return (
    <section>
      <div className="border-b border-[#DDE4DF] pb-7">
        <p className="text-xs font-bold tracking-[0.15em] text-[#4C987C]">
          REVIEWER WORKLIST
        </p>

        <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] text-[#17211D] md:text-5xl">
          통합 리뷰어 검토 워크리스트
        </h1>

        <p className="mt-4 max-w-3xl leading-7 text-[#68736D]">
          약화·중단 점수를 하나의 우선순위로 검토하고,
          상세 화면에서 활동 변화 근거를 확인합니다.
        </p>

        <div className="mt-4">
          <DataModeBadge />
        </div>
      </div>

      <div className="mt-7 grid gap-3 sm:grid-cols-3">
        <StatCard
          label="전체"
          value={`${reviewersWithDecisions.length.toLocaleString()}명`}
        />

        <StatCard
          label="미검토"
          value={`${pendingCount.toLocaleString()}명`}
        />

        <StatCard
          label="검토 완료"
          value={`${completedCount.toLocaleString()}명`}
          note="이 브라우저 기준"
          good
        />
      </div>

      <div className="mt-6">
        <ReviewerFilters
          searchText={searchText}
          onSearchChange={(value) => {
            setSearchText(value);
            setVisibleCount(100);
          }}
          statusFilter={statusFilter}
          onStatusChange={(value) => {
            setStatusFilter(value);
            setVisibleCount(100);
          }}
          judgmentFilters={judgmentFilters}
          onJudgmentFiltersChange={(value) => {
            setJudgmentFilters(value);
            setVisibleCount(100);
          }}
          riskTypeFilter={riskTypeFilter}
          onRiskTypeChange={(value) => {
            setRiskTypeFilter(value);
            setVisibleCount(100);
          }}
          crmRangeFilter={crmRangeFilter}
          onCrmRangeChange={(value) => {
            setCrmRangeFilter(value);
            setVisibleCount(100);
          }}
          sortRule={sortRule}
          onSortChange={setSortRule}
          riskTypes={riskTypes}
        />
      </div>

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          onClick={handleDownloadCsv}
          className="min-h-9 rounded-lg border border-[#DDE4DF] px-4 text-xs font-bold text-[#68736D] transition hover:border-[#137A5A] hover:text-[#137A5A]"
        >
          CSV 다운로드
        </button>
      </div>

      <div className="mt-6">
        <ReviewerTable reviewers={visibleReviewers} />
      </div>

      <div className="mt-5 text-center">
        <p className="text-xs text-[#68736D]">
          전체 {operationsSummary.totalReviewers.toLocaleString()}명 · 조건에
          맞는 {filteredReviewers.length.toLocaleString()}명 중{" "}
          {visibleReviewers.length.toLocaleString()}명 표시
        </p>

        {remainingCount > 0 && (
          <button
            type="button"
            onClick={() => setVisibleCount((count) => count + 100)}
            className="mt-3 min-h-11 rounded-lg border border-[#137A5A] px-6 font-bold text-[#137A5A] transition hover:bg-[#E3F1EA]"
          >
            더 보기 · {Math.min(100, remainingCount)}명 추가
          </button>
        )}
      </div>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs text-[#68736D]">
        {operationsSummary.modelVersion} 실데이터 · 전체 코호트{" "}
        {reviewersWithDecisions.length.toLocaleString()}명
      </footer>
    </section>
  );
}

function StatCard({ label, value, note, good = false }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white px-5 py-4">
      <p className="text-sm text-[#68736D]">
        {label}
      </p>

      <p
        className={[
          "mt-2 text-2xl font-bold",
          good ? "text-[#137A5A]" : "text-[#17211D]",
        ].join(" ")}
      >
        {value}
      </p>

      {note && <p className="mt-1 text-xs text-[#68736D]">{note}</p>}
    </div>
  );
}

export default ReviewerListPage;
