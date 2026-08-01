import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";

import DataModeBadge from "../components/DataModeBadge";
import PageHeader from "../components/common/PageHeader";
import Skeleton from "../components/common/Skeleton";
import ErrorState from "../components/common/ErrorState";
import RegionalBubbleMap from "../components/regional/RegionalBubbleMap";
import RegionalRiskTable from "../components/regional/RegionalRiskTable";
import RegionalTravelRange from "../components/regional/RegionalTravelRange";
import { useOperationsSummary } from "../context/operations-context";
import { loadRegionalDerivedContext, loadRegionalRisk } from "../data";

const sortRules = {
  "활동 리뷰어": (first, second) => second.reviewers - first.reviewers,
  "고위험 비율": (first, second) => second.highRiskRate - first.highRiskRate,
  "고위험 리뷰어": (first, second) => second.highRisk - first.highRisk,
};

function RegionalRiskPage() {
  const operationsSummary = useOperationsSummary();
  const [sortRule, setSortRule] = useState("고위험 비율");
  const [regionalRisk, setRegionalRisk] = useState(null);
  const [error, setError] = useState(null);
  const [hoveredRegion, setHoveredRegion] = useState(null);
  const [viewMode, setViewMode] = useState("priority");
  const [derivedContext, setDerivedContext] = useState(null);

  useEffect(() => {
    let cancelled = false;

    loadRegionalRisk()
      .then((data) => {
        if (!cancelled) setRegionalRisk(data);
      })
      .catch((loadError) => {
        if (!cancelled) setError(loadError.message);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    loadRegionalDerivedContext()
      .then((data) => {
        if (!cancelled && data.available) setDerivedContext(data);
      })
      .catch(() => {
        // Optional v05 data must not block the existing regional screen.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const regions = useMemo(
    () =>
      regionalRisk ? [...regionalRisk.regions].sort(sortRules[sortRule]) : [],
    [regionalRisk, sortRule],
  );

  const totals = useMemo(() => {
    const reviewers = regions.reduce((sum, item) => sum + item.reviewers, 0);
    const highRisk = regions.reduce((sum, item) => sum + item.highRisk, 0);

    return {
      reviewers,
      highRisk,
      highRiskRate: reviewers > 0 ? highRisk / reviewers : 0,
      crmTargets: regions.reduce((sum, item) => sum + item.crmTargets, 0),
    };
  }, [regions]);

  if (error) {
    return (
      <ErrorState message={error} />
    );
  }

  if (!regionalRisk) {
    return <Skeleton rows={5} columns={5} />;
  }

  return (
    <section>
      <PageHeader
        title="콘텐츠 공급 위험"
        description="거주지가 아닌 음식점 리뷰 활동 지역을 기준으로 권역별 콘텐츠 공급 위험을 비교합니다."
        meta={
          <>
            <DataModeBadge />
            <p className="mt-2 text-xs text-[#626D67]">{regions.length}개 권역</p>
          </>
        }
      >
        <div className="flex flex-wrap gap-x-2 gap-y-1 text-xs text-[#626D67]">
          <span>활동 리뷰어 {totals.reviewers.toLocaleString()}</span>
          <span>·</span>
          <span className="text-[#BF3620]">
            고위험 {totals.highRisk.toLocaleString()} ({(totals.highRiskRate * 100).toFixed(1)}%)
          </span>
          <span>·</span>
          <span className="text-[#137A5A]">
            검토 대상 {totals.crmTargets.toLocaleString()}
          </span>
        </div>
      </PageHeader>

      <p className="mt-4 rounded-lg bg-[#E6EFF1] px-4 py-2.5 text-xs leading-5 text-[#356A78]">
        권역은 리뷰어가 {regionalRisk.comparisonYear}~{regionalRisk.selectionYear}년
        관찰 구간에 가장 많이 리뷰한 지역(state)입니다. 거주지, 직장, 실제 생활
        반경을 추론하지 않습니다.
      </p>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-1.5">
          <button
            type="button"
            onClick={() => setViewMode("priority")}
            className={[
              "min-h-8 rounded-lg border px-3 text-xs font-medium transition",
              viewMode === "priority"
                ? "border-[#137A5A] bg-[#E3F1EA] text-[#137A5A]"
                : "border-[#DDE4DF] text-[#626D67] hover:border-[#137A5A]",
            ].join(" ")}
          >
            권역 우선순위
          </button>
          <button
            type="button"
            onClick={() => setViewMode("travel")}
            className={[
              "min-h-8 rounded-lg border px-3 text-xs font-medium transition",
              viewMode === "travel"
                ? "border-[#137A5A] bg-[#E3F1EA] text-[#137A5A]"
                : "border-[#DDE4DF] text-[#626D67] hover:border-[#137A5A]",
            ].join(" ")}
          >
            탐방 범위
          </button>
          {derivedContext && (
            <button
              type="button"
              onClick={() => setViewMode("supply")}
              className={[
                "min-h-8 rounded-lg border px-3 text-xs font-medium transition",
                viewMode === "supply"
                  ? "border-[#137A5A] bg-[#E3F1EA] text-[#137A5A]"
                  : "border-[#DDE4DF] text-[#626D67] hover:border-[#137A5A]",
              ].join(" ")}
            >
              리뷰 공급 변화
            </button>
          )}
        </div>

        {viewMode === "priority" && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-[#626D67]">정렬</span>
            {Object.keys(sortRules).map((rule) => (
              <button
                key={rule}
                type="button"
                onClick={() => setSortRule(rule)}
                className={[
                  "min-h-8 rounded-full border px-3 text-xs font-medium transition",
                  sortRule === rule
                    ? "border-[#137A5A] bg-[#E3F1EA] text-[#137A5A]"
                    : "border-[#DDE4DF] text-[#626D67] hover:border-[#137A5A]",
                ].join(" ")}
              >
                {rule}
              </button>
            ))}
          </div>
        )}
      </div>

      {viewMode === "priority" ? (
        <>
          <div className="mt-4">
            <RegionalBubbleMap
              regions={regions}
              hoveredRegion={hoveredRegion}
              onHoverRegion={setHoveredRegion}
            />
          </div>

          <div className="mt-6">
            <p className="mb-2 text-xs text-[#626D67]">
              표본 {regionalRisk.minimumReviewers}명 미만 권역은 비율이 흔들릴 수
              있어 별도로 표시합니다. 지도와 표는 서로 연동됩니다.
            </p>

            <RegionalRiskTable
              regions={regions}
              minimumReviewers={regionalRisk.minimumReviewers}
              hoveredRegion={hoveredRegion}
              onHoverRegion={setHoveredRegion}
            />
          </div>
        </>
      ) : viewMode === "travel" ? (
        <div className="mt-4">
          <RegionalTravelRange />
        </div>
      ) : (
        <RegionalSupplyContext data={derivedContext} />
      )}

      <div className="mt-10 rounded-xl border border-[#DDE4DF] bg-white p-6">
        <h2 className="text-lg font-bold text-[#17211D]">운영 연결</h2>

        <p className="mt-3 text-sm leading-7 text-[#626D67]">
          위험 권역을 확인한 뒤 리뷰어 워크리스트에서 개별 활동 변화와 개입
          필요성을 검토합니다.
        </p>

        <Link
          to="/reviewers"
          className="mt-5 inline-flex min-h-11 items-center justify-center rounded-lg bg-[#137A5A] px-5 font-bold text-white transition hover:bg-[#185C46]"
        >
          리뷰어 워크리스트 열기
        </Link>
      </div>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs leading-5 text-[#626D67]">
        Reviewer Retention · {operationsSummary.dataModeLabel} data · 고위험
        비율은 운영 검토 우선순위이며 실제 콘텐츠 소멸 확률이 아닙니다.
      </footer>
    </section>
  );
}

function RegionalSupplyContext({ data }) {
  const regions = [...data.regions].sort(
    (first, second) => second.reviewSupplyChangeRate - first.reviewSupplyChangeRate,
  );
  const totalReviews = regions.reduce((sum, region) => sum + region.reviewCount, 0);
  const previousReviews = regions.reduce(
    (sum, region) => sum + (region.previousYearReviewCount ?? 0),
    0,
  );
  const totalChangeRate = previousReviews > 0
    ? (totalReviews - previousReviews) / previousReviews
    : 0;
  const newcomers = regions.reduce((sum, region) => sum + region.newPowerReviewers, 0);

  return (
    <div className="mt-4 rounded-xl border border-[#DDE4DF] bg-white p-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <SupplyMetric label={`${data.selectionYear}년 전체 음식점 리뷰`} value={totalReviews.toLocaleString()} />
        <SupplyMetric label="전년 대비 리뷰 공급" value={`${totalChangeRate >= 0 ? "+" : ""}${(totalChangeRate * 100).toFixed(1)}%`} />
        <SupplyMetric label="신규 파워 리뷰어" value={`${newcomers.toLocaleString()}명`} />
      </div>
      <p className="mt-4 text-xs leading-5 text-[#626D67]">
        전체 음식점 리뷰 기준으로 재계산해 파워 리뷰어 코호트 선정 편향을 제거했습니다. 신규 유입은 최초 코호트 진입 연도에 한 번만 집계합니다.
      </p>
      <div className="mt-4 overflow-x-auto">
        <table className="min-w-[640px] w-full text-sm">
          <thead>
            <tr className="border-b border-[#DDE4DF] text-left text-xs text-[#626D67]">
              <th className="py-2">권역</th><th className="py-2 text-right">리뷰 공급</th><th className="py-2 text-right">전년 대비</th><th className="py-2 text-right">활동 리뷰어</th><th className="py-2 text-right">신규 파워 리뷰어</th>
            </tr>
          </thead>
          <tbody>
            {regions.map((region) => (
              <tr key={region.region} className="border-b border-[#F1F4F1] last:border-0">
                <td className="py-2 font-bold text-[#17211D]">{region.region}</td>
                <td className="py-2 text-right">{region.reviewCount.toLocaleString()}</td>
                <td className={`py-2 text-right font-medium ${region.reviewSupplyChangeRate < 0 ? "text-[#BF3620]" : "text-[#137A5A]"}`}>
                  {region.reviewSupplyChangeRate >= 0 ? "+" : ""}{(region.reviewSupplyChangeRate * 100).toFixed(1)}%
                </td>
                <td className="py-2 text-right text-[#626D67]">{region.activeReviewers.toLocaleString()}</td>
                <td className="py-2 text-right text-[#626D67]">{region.newPowerReviewers.toLocaleString()}명</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SupplyMetric({ label, value }) {
  return (
    <div className="rounded-lg bg-[#F7F8F5] p-4">
      <p className="text-xs text-[#626D67]">{label}</p>
      <p className="mt-1 text-xl font-bold text-[#17211D]">{value}</p>
    </div>
  );
}

export default RegionalRiskPage;
