import { useMemo, useState } from "react";
import { getDecisions } from "../services/decisionStorage";
import ReviewerFilters from "../components/reviewers/ReviewerFilters";
import ReviewerTable from "../components/reviewers/ReviewerTable";
import { reviewerData } from "../mocks/reviewerData";

function ReviewerListPage() {
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState("전체");
  const [judgmentFilter, setJudgmentFilter] = useState("전체");
  const [riskTypeFilter, setRiskTypeFilter] = useState("전체");
  const [sortRule, setSortRule] = useState("우선순위");
  const [visibleCount, setVisibleCount] = useState(8);
  const [decisions] = useState(() => getDecisions());

  const reviewersWithDecisions = useMemo(
    () =>
      reviewerData.map((reviewer) => ({
        ...reviewer,
        managerDecision: decisions[reviewer.userId] ?? null,
      })),
    [decisions],
  );  
  
  const completedCount = reviewersWithDecisions.filter(
    (reviewer) => reviewer.managerDecision,
  ).length;

  const pendingCount = reviewersWithDecisions.length - completedCount;

  const riskTypes = [
    ...new Set(reviewersWithDecisions.map((reviewer) => reviewer.riskType)),
  ];

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

    if (judgmentFilter !== "전체") {
      result = result.filter(
        (reviewer) => reviewer.modelJudgment === judgmentFilter,
      );
    }

    if (riskTypeFilter !== "전체") {
      result = result.filter(
        (reviewer) => reviewer.riskType === riskTypeFilter,
      );
    }

    if (sortRule === "리뷰 공백") {
      result.sort(
        (first, second) =>
          second.recentRecencyDays - first.recentRecencyDays,
      );
    } else if (sortRule === "최근 활동 월") {
      result.sort(
        (first, second) =>
          first.recentActiveMonths - second.recentActiveMonths,
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
    judgmentFilter,
    riskTypeFilter,
    sortRule,
    reviewersWithDecisions,
  ]);

  const visibleReviewers = filteredReviewers.slice(0, visibleCount);
  const remainingCount =
    filteredReviewers.length - visibleReviewers.length;

  return (
    <section>
      <div className="border-b border-[#DDE4DF] pb-7">
        <p className="text-xs font-bold tracking-[0.15em] text-[#4C987C]">
          REVIEWER WORKLIST · REACT
        </p>

        <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] text-[#17211D] md:text-5xl">
          통합 리뷰어 검토 워크리스트
        </h1>

        <p className="mt-4 max-w-3xl leading-7 text-[#68736D]">
          약화·중단 점수를 하나의 우선순위로 검토하고,
          상세 화면에서 활동 변화 근거를 확인합니다.
        </p>

        <span className="mt-4 inline-flex rounded-full bg-[#17211D] px-3 py-1 text-xs font-bold text-white">
          DEMO 데이터
        </span>
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
          good
        />
      </div>

      <div className="mt-6">
        <ReviewerFilters
          searchText={searchText}
          onSearchChange={(value) => {
            setSearchText(value);
            setVisibleCount(8);
          }}
          statusFilter={statusFilter}
          onStatusChange={(value) => {
            setStatusFilter(value);
            setVisibleCount(8);
          }}
          judgmentFilter={judgmentFilter}
          onJudgmentChange={(value) => {
            setJudgmentFilter(value);
            setVisibleCount(8);
          }}
          riskTypeFilter={riskTypeFilter}
          onRiskTypeChange={(value) => {
            setRiskTypeFilter(value);
            setVisibleCount(8);
          }}
          sortRule={sortRule}
          onSortChange={setSortRule}
          riskTypes={riskTypes}
        />
      </div>

      <div className="mt-6">
        <ReviewerTable reviewers={visibleReviewers} />
      </div>

      <div className="mt-5 text-center">
        <p className="text-xs text-[#68736D]">
          {filteredReviewers.length.toLocaleString()}명 중{" "}
          {visibleReviewers.length.toLocaleString()}명 표시
        </p>

        {remainingCount > 0 && (
          <button
            type="button"
            onClick={() => setVisibleCount((count) => count + 8)}
            className="mt-3 min-h-11 rounded-lg border border-[#137A5A] px-6 font-bold text-[#137A5A] transition hover:bg-[#E3F1EA]"
          >
            더 보기 · {Math.min(8, remainingCount)}명 추가
          </button>
        )}
      </div>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs text-[#68736D]">
        현재 목록은 화면 기능 검증을 위한 합성 DEMO 데이터입니다.
      </footer>
    </section>
  );
}

function StatCard({ label, value, good = false }) {
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
    </div>
  );
}

export default ReviewerListPage;