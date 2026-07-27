import { useMemo, useState } from "react";
import { Link } from "react-router";

import RegionalFilters from "../components/regional/RegionalFilters";
import RegionalRiskChart from "../components/regional/RegionalRiskChart";
import RegionalRiskTable from "../components/regional/RegionalRiskTable";
import { regionalRiskData } from "../mocks/regionalRiskData";

function RegionalRiskPage() {
  const [searchText, setSearchText] = useState("");
  const [stateFilter, setStateFilter] = useState("전체");
  const [riskLevelFilter, setRiskLevelFilter] =
    useState("전체");
  const [sortRule, setSortRule] = useState("우선순위");

  const states = useMemo(
    () => [
      ...new Set(
        regionalRiskData.map((region) => region.state),
      ),
    ],
    [],
  );

  const riskLevels = [
    "매우 높음",
    "높음",
    "보통",
    "낮음",
  ];

  const visibleRegions = useMemo(() => {
    let result = [...regionalRiskData];

    if (searchText.trim()) {
      const keyword = searchText.trim().toLowerCase();

      result = result.filter((region) =>
        region.city.toLowerCase().includes(keyword),
      );
    }

    if (stateFilter !== "전체") {
      result = result.filter(
        (region) => region.state === stateFilter,
      );
    }

    if (riskLevelFilter !== "전체") {
      result = result.filter(
        (region) =>
          region.riskLevel === riskLevelFilter,
      );
    }

    if (sortRule === "위험률") {
      result.sort(
        (first, second) =>
          second.riskRate - first.riskRate,
      );
    } else if (sortRule === "위험 리뷰어") {
      result.sort(
        (first, second) =>
          second.weakened +
          second.stopped -
          (first.weakened + first.stopped),
      );
    } else if (sortRule === "전체 리뷰어") {
      result.sort(
        (first, second) =>
          second.totalReviewers -
          first.totalReviewers,
      );
    } else {
      result.sort(
        (first, second) =>
          second.priorityScore -
          first.priorityScore,
      );
    }

    return result;
  }, [
    searchText,
    stateFilter,
    riskLevelFilter,
    sortRule,
  ]);

  const summary = useMemo(() => {
    const totalReviewers = visibleRegions.reduce(
      (sum, region) =>
        sum + region.totalReviewers,
      0,
    );

    const weakenedReviewers = visibleRegions.reduce(
      (sum, region) =>
        sum + region.weakened,
      0,
    );

    const stoppedReviewers = visibleRegions.reduce(
      (sum, region) =>
        sum + region.stopped,
      0,
    );

    const riskReviewers =
      weakenedReviewers + stoppedReviewers;

    const riskRate =
      totalReviewers > 0
        ? riskReviewers / totalReviewers
        : 0;

    return {
      totalReviewers,
      weakenedReviewers,
      stoppedReviewers,
      riskReviewers,
      riskRate,
    };
  }, [visibleRegions]);

  return (
    <section>
      <div className="flex flex-col justify-between gap-5 border-b border-[#DDE4DF] pb-7 lg:flex-row">
        <div>
          <p className="text-xs font-bold tracking-[0.15em] text-[#4C987C]">
            CONTENT RISK · REACT
          </p>

          <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] text-[#17211D] md:text-5xl">
            콘텐츠 위험 지역 분석
          </h1>

          <p className="mt-4 max-w-3xl leading-7 text-[#68736D]">
            파워 리뷰어의 활동 약화와 중단이 지역별 음식점
            리뷰 공급에 미칠 수 있는 위험을 비교합니다.
          </p>
        </div>

        <div className="lg:text-right">
          <span className="inline-flex rounded-full bg-[#17211D] px-3 py-1 text-xs font-bold text-white">
            DEMO 지역 데이터
          </span>

          <p className="mt-3 text-sm text-[#68736D]">
            현재 표시 지역
          </p>

          <p className="mt-1 text-2xl font-bold text-[#137A5A]">
            {visibleRegions.length}개
          </p>
        </div>
      </div>

      <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          label="전체 리뷰어"
          value={`${summary.totalReviewers.toLocaleString()}명`}
        />

        <SummaryCard
          label="약화 우세"
          value={`${summary.weakenedReviewers.toLocaleString()}명`}
          tone="warning"
        />

        <SummaryCard
          label="중단 우세"
          value={`${summary.stoppedReviewers.toLocaleString()}명`}
          tone="critical"
        />

        <SummaryCard
          label="콘텐츠 위험률"
          value={`${(summary.riskRate * 100).toFixed(1)}%`}
          tone="good"
        />
      </div>

      <div className="mt-6">
        <RegionalFilters
          searchText={searchText}
          onSearchChange={setSearchText}
          stateFilter={stateFilter}
          onStateChange={setStateFilter}
          riskLevelFilter={riskLevelFilter}
          onRiskLevelChange={setRiskLevelFilter}
          sortRule={sortRule}
          onSortChange={setSortRule}
          states={states}
          riskLevels={riskLevels}
        />
      </div>

      <div className="mt-7">
        <RegionalRiskChart data={visibleRegions} />
      </div>

      <div className="mt-8">
        <div className="mb-4">
          <h2 className="text-xl font-bold text-[#17211D]">
            지역 우선 검토 목록
          </h2>

          <p className="mt-2 text-sm text-[#68736D]">
            위험률과 활동 감소 신호를 함께 확인합니다.
          </p>
        </div>

        <RegionalRiskTable regions={visibleRegions} />
      </div>

      <div className="mt-8 grid gap-5 lg:grid-cols-2">
        <div className="rounded-xl border border-[#DDE4DF] bg-white p-6">
          <h2 className="text-lg font-bold text-[#17211D]">
            콘텐츠 위험률 해석
          </h2>

          <p className="mt-3 text-sm leading-7 text-[#68736D]">
            콘텐츠 위험률은 해당 지역의 전체 파워 리뷰어 중
            약화 우세 또는 중단 우세로 분류된 리뷰어 비율입니다.
            실제 음식점 콘텐츠가 사라질 확률을 의미하지는
            않습니다.
          </p>
        </div>

        <div className="rounded-xl border border-[#DDE4DF] bg-white p-6">
          <h2 className="text-lg font-bold text-[#17211D]">
            운영 연결
          </h2>

          <p className="mt-3 text-sm leading-7 text-[#68736D]">
            위험 지역을 확인한 뒤 리뷰어 워크리스트에서 개별
            활동 변화와 개입 필요성을 추가로 검토합니다.
          </p>

          <Link
            to="/reviewers"
            className="mt-5 inline-flex min-h-11 items-center justify-center rounded-lg bg-[#137A5A] px-5 font-bold text-white transition hover:bg-[#185C46]"
          >
            리뷰어 워크리스트 열기
          </Link>
        </div>
      </div>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs text-[#68736D]">
        Reviewer Retention · DEMO regional data · 지역 위험은
        운영 검토 우선순위이며 실제 콘텐츠 소멸 확률이 아닙니다.
      </footer>
    </section>
  );
}

function SummaryCard({
  label,
  value,
  tone = "default",
}) {
  const valueStyle = {
    default: "text-[#17211D]",
    warning: "text-[#A66A18]",
    critical: "text-[#E15D47]",
    good: "text-[#137A5A]",
  };

  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white px-5 py-4">
      <p className="text-sm text-[#68736D]">
        {label}
      </p>

      <p
        className={[
          "mt-2 text-2xl font-bold",
          valueStyle[tone],
        ].join(" ")}
      >
        {value}
      </p>
    </div>
  );
}

export default RegionalRiskPage;