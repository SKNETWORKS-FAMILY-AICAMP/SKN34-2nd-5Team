import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";

import DataModeBadge from "../components/DataModeBadge";
import RegionalRiskChart from "../components/regional/RegionalRiskChart";
import RegionalRiskTable from "../components/regional/RegionalRiskTable";
import { useOperationsSummary } from "../context/operations-context";
import { loadRegionalRisk } from "../data";

const sortRules = {
  "활동 리뷰어": (first, second) => second.reviewers - first.reviewers,
  "고위험 비율": (first, second) => second.highRiskRate - first.highRiskRate,
  "고위험 리뷰어": (first, second) => second.highRisk - first.highRisk,
};

// Kept from the pre-data version so the screen still explains what it will do
// once campaign and supply history land.
const connectedCapabilities = [
  {
    title: "지역 우선순위",
    description: "위험 리뷰어 규모와 비율을 함께 비교",
    status: "현재 사용 가능",
  },
  {
    title: "신규 리뷰어 유입",
    description: "지역별 콘텐츠 생산 기반 관찰",
    status: "데이터 연결 필요",
  },
  {
    title: "리뷰 공급 변화",
    description: "음식점 리뷰 감소 지역 탐지 · 코호트 정의상 항상 증가로 나와 지표 재설계 필요",
    status: "데이터 연결 필요",
  },
  {
    title: "탐방 미션 후보",
    description: "운영 검토 후 지역 미션 설계",
    status: "규칙 기반 프로토타입",
  },
];

function RegionalRiskPage() {
  const operationsSummary = useOperationsSummary();
  const [sortRule, setSortRule] = useState("활동 리뷰어");
  const [regionalRisk, setRegionalRisk] = useState(null);
  const [error, setError] = useState(null);

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
      <section className="rounded-xl border border-[#F0D9D4] bg-[#FBF1EF] p-6 text-sm text-[#8A3B2E]">
        권역 데이터를 불러오지 못했습니다: {error}
      </section>
    );
  }

  if (!regionalRisk) {
    return (
      <section className="p-6 text-sm text-[#68736D]">불러오는 중…</section>
    );
  }

  return (
    <section>
      <div className="flex flex-col justify-between gap-5 border-b border-[#DDE4DF] pb-7 lg:flex-row">
        <div>
          <p className="text-xs font-bold tracking-[0.15em] text-[#4C987C]">
            REGIONAL CONTENT RISK
          </p>

          <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] text-[#17211D] md:text-5xl">
            콘텐츠 공급 위험을 권역 단위로 봅니다
          </h1>

          <p className="mt-4 max-w-3xl leading-7 text-[#68736D]">
            거주지가 아닌 음식점 리뷰 활동 지역을 기준으로 권역별 콘텐츠 공급
            위험을 비교합니다.
          </p>
        </div>

        <div className="lg:text-right">
          <DataModeBadge />

          <p className="mt-3 text-sm text-[#68736D]">전체 권역</p>

          <p className="mt-1 text-2xl font-bold text-[#137A5A]">
            {regions.length}개
          </p>
        </div>
      </div>

      <p className="mt-5 rounded-lg bg-[#E6EFF1] px-4 py-3 text-xs leading-5 text-[#356A78]">
        권역은 리뷰어가 {regionalRisk.comparisonYear}~{regionalRisk.selectionYear}년
        관찰 구간에 가장 많이 리뷰한 지역(state)입니다. 거주지, 직장, 실제 생활
        반경을 추론하지 않습니다.
      </p>

      <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          label="활동 리뷰어"
          value={`${totals.reviewers.toLocaleString()}명`}
          note={`전체 ${regionalRisk.totalReviewers.toLocaleString()}명 중 ${(
            (regionalRisk.coveredReviewers / regionalRisk.totalReviewers) *
            100
          ).toFixed(1)}% 권역 확인`}
        />

        <SummaryCard
          label="고위험 리뷰어"
          value={`${totals.highRisk.toLocaleString()}명`}
          tone="critical"
          note="약화 우세 + 중단 우세"
        />

        <SummaryCard
          label="고위험 비율"
          value={`${(totals.highRiskRate * 100).toFixed(1)}%`}
          tone="warning"
        />

        <SummaryCard
          label="통합 검토 대상"
          value={`${totals.crmTargets.toLocaleString()}명`}
          tone="good"
          note="통합 우선순위 상위 20%"
        />
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-[#68736D]">정렬</span>

        {Object.keys(sortRules).map((rule) => (
          <button
            key={rule}
            type="button"
            onClick={() => setSortRule(rule)}
            className={[
              "rounded-full border px-3 py-1 text-xs font-bold transition",
              sortRule === rule
                ? "border-[#137A5A] bg-[#E3F1EA] text-[#137A5A]"
                : "border-[#DDE4DF] text-[#68736D] hover:border-[#137A5A]",
            ].join(" ")}
          >
            {rule}
          </button>
        ))}
      </div>

      <div className="mt-6">
        <RegionalRiskChart regions={regions} />
      </div>

      <div className="mt-8">
        <div className="mb-4">
          <h2 className="text-xl font-bold text-[#17211D]">
            권역 우선순위
          </h2>

          <p className="mt-2 text-sm text-[#68736D]">
            표본 {regionalRisk.minimumReviewers}명 미만 권역은 비율이 흔들릴 수
            있어 별도로 표시합니다.
          </p>
        </div>

        <RegionalRiskTable
          regions={regions}
          minimumReviewers={regionalRisk.minimumReviewers}
        />
      </div>

      <div className="mt-10">
        <h2 className="text-xl font-bold text-[#17211D]">연결 후 운영 기능</h2>

        <p className="mt-2 text-sm text-[#68736D]">
          권역 집계가 연결되면서 일부 기능이 활성화됐고, 나머지는 추가 데이터가
          필요합니다.
        </p>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          {connectedCapabilities.map((item) => (
            <div
              key={item.title}
              className="rounded-xl border border-[#DDE4DF] bg-white p-5"
            >
              <div className="flex items-center justify-between gap-3">
                <p className="font-bold text-[#17211D]">{item.title}</p>

                <span className="whitespace-nowrap rounded bg-[#F1F4F1] px-2 py-1 text-xs text-[#68736D]">
                  {item.status}
                </span>
              </div>

              <p className="mt-2 text-sm text-[#68736D]">{item.description}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-10 rounded-xl border border-[#DDE4DF] bg-white p-6">
        <h2 className="text-lg font-bold text-[#17211D]">운영 연결</h2>

        <p className="mt-3 text-sm leading-7 text-[#68736D]">
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

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs leading-5 text-[#68736D]">
        Reviewer Retention · {operationsSummary.dataModeLabel} data · 고위험
        비율은 운영 검토 우선순위이며 실제 콘텐츠 소멸 확률이 아닙니다.
      </footer>
    </section>
  );
}

function SummaryCard({ label, value, note, tone = "default" }) {
  const valueStyle = {
    default: "text-[#17211D]",
    warning: "text-[#A66A18]",
    critical: "text-[#E15D47]",
    good: "text-[#137A5A]",
  };

  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white px-5 py-4">
      <p className="text-sm text-[#68736D]">{label}</p>

      <p className={["mt-2 text-2xl font-bold", valueStyle[tone]].join(" ")}>
        {value}
      </p>

      {note && <p className="mt-1 text-xs text-[#68736D]">{note}</p>}
    </div>
  );
}

export default RegionalRiskPage;
