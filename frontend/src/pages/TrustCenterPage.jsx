import { useMemo, useState } from "react";

import ModelPerformanceChart from "../components/trust/ModelPerformanceChart";
import RoadmapTimeline from "../components/trust/RoadmapTimeline";
import ValidationChecklist from "../components/trust/ValidationChecklist";
import {
  featureGroups,
  modelPerformanceData,
  roadmapData,
  trustSummary,
  validationChecks,
} from "../mocks/trustCenterData";

const tabs = [
  {
    key: "performance",
    label: "모델 성능",
  },
  {
    key: "validation",
    label: "검증 체크",
  },
  {
    key: "features",
    label: "피처 근거",
  },
  {
    key: "roadmap",
    label: "제품 로드맵",
  },
];

function TrustCenterPage() {
  const [activeTab, setActiveTab] =
    useState("performance");

  const completedValidationCount = useMemo(
    () =>
      validationChecks.filter(
        (check) => check.status === "완료",
      ).length,
    [],
  );

  const pendingValidationCount =
    validationChecks.length - completedValidationCount;

  const captureRate =
    trustSummary.selectedReviewers > 0
      ? trustSummary.capturedReviewers /
        trustSummary.selectedReviewers
      : 0;

  return (
    <section>
      <div className="flex flex-col justify-between gap-5 border-b border-[#DDE4DF] pb-7 lg:flex-row">
        <div>
          <p className="text-xs font-bold tracking-[0.15em] text-[#4C987C]">
            TRUST CENTER · {trustSummary.modelVersion}
          </p>

          <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] text-[#17211D] md:text-5xl">
            모델 신뢰·제품 로드맵
          </h1>

          <p className="mt-4 max-w-3xl leading-7 text-[#68736D]">
            모델 성능 수치뿐 아니라 데이터 분리, 누수 방지,
            점수 해석과 제품 준비 상태를 함께 확인합니다.
          </p>
        </div>

        <div className="lg:text-right">
          <span className="inline-flex rounded-full bg-[#17211D] px-3 py-1 text-xs font-bold text-white">
            {trustSummary.dataMode}
          </span>

          <p className="mt-3 text-sm text-[#68736D]">
            검증 스냅샷
          </p>

          <p className="mt-1 font-bold text-[#17211D]">
            {trustSummary.validationPeriod}
          </p>
        </div>
      </div>

      <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          label="정밀도"
          value={formatPercent(trustSummary.precision)}
          description="검토 대상으로 선택한 리뷰어 중 실제 활동 저하 대상 비율"
          tone="good"
        />

        <SummaryCard
          label="재현율"
          value={formatPercent(trustSummary.recall)}
          description="전체 활동 저하 대상 중 현재 큐가 포착한 비율"
          tone="watch"
        />

        <SummaryCard
          label="Lift"
          value={`${trustSummary.lift.toFixed(2)}배`}
          description="무작위 선택 대비 실제 활동 저하 대상 포함 정도"
          tone="good"
        />

        <SummaryCard
          label="선택 대상 내 포착"
          value={formatPercent(captureRate)}
          description={`${trustSummary.selectedReviewers.toLocaleString()}명 중 ${trustSummary.capturedReviewers.toLocaleString()}명`}
        />
      </div>

      <div className="mt-8 rounded-xl border border-[#DDE4DF] bg-white p-5">
        <h2 className="text-lg font-bold text-[#17211D]">
          점수 해석 시 주의사항
        </h2>

        <p className="mt-3 text-sm leading-7 text-[#68736D]">
          현재 유지·약화·중단 클래스 점수는 실제 이탈 확률이
          아닙니다. 여러 리뷰어 중 누구부터 검토할지를 정하기
          위한 상대적 운영 우선순위입니다.
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
          <NoticeBadge text="이탈 확률 아님" />
          <NoticeBadge text="사후 Test 검증" />
          <NoticeBadge text="운영자 최종 판단 필요" />
          <NoticeBadge text="DEMO 수치 포함" />
        </div>
      </div>

      <div className="mt-8 flex overflow-x-auto border-b border-[#DDE4DF]">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={[
              "min-w-32 border-b-2 px-5 py-3 text-sm font-bold transition",
              activeTab === tab.key
                ? "border-[#137A5A] text-[#137A5A]"
                : "border-transparent text-[#68736D] hover:text-[#137A5A]",
            ].join(" ")}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {activeTab === "performance" && (
          <div className="space-y-6">
            <ModelPerformanceChart
              data={modelPerformanceData}
            />

            <div className="grid gap-5 lg:grid-cols-2">
              <ExplanationCard
                title="정밀도가 높은 이유"
                description="상위 우선순위 대상만 좁게 선택했기 때문에 검토 큐 안에는 실제 활동 저하 대상이 비교적 많이 포함됩니다."
              />

              <ExplanationCard
                title="재현율이 낮은 이유"
                description="전체 위험 리뷰어를 모두 찾는 것보다 제한된 운영 용량 안에서 정확한 대상을 우선 검토하도록 설계했기 때문입니다."
              />
            </div>
          </div>
        )}

        {activeTab === "validation" && (
          <div>
            <div className="mb-5 grid gap-4 sm:grid-cols-2">
              <CompactCard
                label="검증 완료"
                value={`${completedValidationCount}개`}
                tone="good"
              />

              <CompactCard
                label="추가 검증 필요"
                value={`${pendingValidationCount}개`}
                tone="warning"
              />
            </div>

            <ValidationChecklist
              checks={validationChecks}
            />
          </div>
        )}

        {activeTab === "features" && (
          <div>
            <div className="grid gap-5 md:grid-cols-2">
              {featureGroups.map((group) => (
                <FeatureGroup
                  key={group.title}
                  group={group}
                />
              ))}
            </div>

            <div className="mt-6 rounded-xl bg-[#F1F4F1] p-6">
              <h3 className="font-bold text-[#17211D]">
                피처 중요도 해석 원칙
              </h3>

              <p className="mt-3 text-sm leading-7 text-[#68736D]">
                피처 중요도가 높다는 사실만으로 활동 저하의
                직접 원인이라고 해석해서는 안 됩니다. 중요도는
                모델 예측에 기여한 정도이며 인과관계를 의미하지
                않습니다.
              </p>
            </div>
          </div>
        )}

        {activeTab === "roadmap" && (
          <div className="grid gap-7 xl:grid-cols-[1.3fr_0.7fr]">
            <RoadmapTimeline roadmap={roadmapData} />

            <div className="space-y-5">
              <RoadmapSummary
                title="현재 단계"
                value="React 프론트엔드"
                description="Streamlit 화면을 재사용 가능한 React 컴포넌트로 전환하고 있습니다."
                tone="warning"
              />

              <RoadmapSummary
                title="다음 단계"
                value="FastAPI 데이터 연결"
                description="DEMO 데이터를 제거하고 Python 모델 결과를 API로 전달합니다."
                tone="good"
              />

              <RoadmapSummary
                title="운영 전 필수"
                value="효과 검증"
                description="플레이북 실행이 실제 리뷰 활동 회복으로 이어지는지 검증해야 합니다."
              />
            </div>
          </div>
        )}
      </div>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs text-[#68736D]">
        Reviewer Retention · DEMO trust center · 실제 모델 성능과
        검증 결과는 백엔드 연결 후 교체합니다.
      </footer>
    </section>
  );
}

function formatPercent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function SummaryCard({
  label,
  value,
  description,
  tone = "default",
}) {
  const valueStyle = {
    default: "text-[#17211D]",
    good: "text-[#137A5A]",
    watch: "text-[#356A78]",
  };

  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <p className="text-sm text-[#68736D]">
        {label}
      </p>

      <p
        className={[
          "mt-2 text-3xl font-bold",
          valueStyle[tone],
        ].join(" ")}
      >
        {value}
      </p>

      <p className="mt-3 text-xs leading-5 text-[#68736D]">
        {description}
      </p>
    </div>
  );
}

function NoticeBadge({ text }) {
  return (
    <span className="rounded-full bg-[#F1F4F1] px-3 py-1 text-xs font-bold text-[#68736D]">
      {text}
    </span>
  );
}

function ExplanationCard({ title, description }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-6">
      <h3 className="font-bold text-[#17211D]">
        {title}
      </h3>

      <p className="mt-3 text-sm leading-7 text-[#68736D]">
        {description}
      </p>
    </div>
  );
}

function CompactCard({
  label,
  value,
  tone = "default",
}) {
  const valueStyle = {
    default: "text-[#17211D]",
    good: "text-[#137A5A]",
    warning: "text-[#A66A18]",
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

function FeatureGroup({ group }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-6">
      <h3 className="text-lg font-bold text-[#17211D]">
        {group.title}
      </h3>

      <ul className="mt-4 space-y-3">
        {group.features.map((feature) => (
          <li
            key={feature}
            className="flex gap-3 text-sm text-[#68736D]"
          >
            <span className="font-bold text-[#137A5A]">
              ✓
            </span>

            <span>{feature}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RoadmapSummary({
  title,
  value,
  description,
  tone = "default",
}) {
  const valueStyle = {
    default: "text-[#17211D]",
    good: "text-[#137A5A]",
    warning: "text-[#A66A18]",
  };

  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <p className="text-sm text-[#68736D]">
        {title}
      </p>

      <p
        className={[
          "mt-2 text-xl font-bold",
          valueStyle[tone],
        ].join(" ")}
      >
        {value}
      </p>

      <p className="mt-3 text-sm leading-6 text-[#68736D]">
        {description}
      </p>
    </div>
  );
}

export default TrustCenterPage;