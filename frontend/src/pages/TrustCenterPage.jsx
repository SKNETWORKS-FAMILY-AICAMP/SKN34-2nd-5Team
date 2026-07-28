import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import DataModeBadge from "../components/DataModeBadge";
import { operationsSummary, trustData } from "../data";

const tabs = [
  { key: "performance", label: "성능과 Top-K" },
  { key: "split", label: "시간 분할·누수 방지" },
  { key: "features", label: "피처 근거" },
  { key: "roadmap", label: "제품 상태·로드맵" },
];

// Streamlit's "누수 방지 원칙" capability grid (views/trust_center.py).
const leakagePrinciples = [
  {
    title: "미래 정보 제외",
    description: "선정·피처 마감 연도까지의 활동만 입력으로 사용합니다.",
    status: "현재 사용 가능",
  },
  {
    title: "정답 분리",
    description: "검증 연도의 실제 상태는 학습에 사용하지 않습니다.",
    status: "현재 사용 가능",
  },
  {
    title: "순위 점수",
    description: "클래스 점수는 보정 확률이 아니라 상대 우선순위입니다.",
    status: "현재 사용 가능",
  },
  {
    title: "추론 제한",
    description: "거주지·직장 등 관찰되지 않은 속성은 추론하지 않습니다.",
    status: "현재 사용 가능",
  },
];

// Product capability roadmap — what the product offers its users, which is what
// the Streamlit roadmap tracks (not the React/FastAPI migration schedule).
const productRoadmap = [
  {
    title: "운영 홈 · 검토 큐",
    need: "v04 예측 프로파일",
    value: "매 세션 우선 검토 대상 확인",
    status: "현재 사용 가능",
  },
  {
    title: "위험 유형 플레이북",
    need: "규칙 기반 위험 유형 분류",
    value: "판단별 대응 전략 참고",
    status: "규칙 기반 프로토타입",
  },
  {
    title: "월별 활동 타임라인",
    need: "원천 리뷰 데이터 직접 집계 (comparison~selection 구간)",
    value: "활동 감소 시작점과 회복 확인",
    status: "현재 사용 가능 · React 단독",
  },
  {
    title: "지역 콘텐츠 위험",
    need: "지역 집계 파일 · 최소 표본 기준",
    value: "지역 단위 공급 위험 비교",
    status: "정의·데이터 필요",
  },
  {
    title: "캠페인 성과 추적",
    need: "개입 이력 · 채널 · 결과",
    value: "개입 효과 검증",
    status: "고도화 예정",
  },
  {
    title: "개인별 SHAP · 보정 확률",
    need: "설명 모델 · 확률 보정",
    value: "개인 단위 근거와 실제 확률 제시",
    status: "고도화 예정",
  },
];

const stateLabels = {
  retained: "파워 지위 유지",
  weakened: "파워 지위 약화",
  stopped: "리뷰 활동 중단",
};

function percent(value, digits = 1) {
  return `${(value * 100).toFixed(digits)}%`;
}

function TrustCenterPage() {
  const [activeTab, setActiveTab] = useState("performance");

  const { overall, classPerformance, confusionMatrix, topK } = trustData;
  const v03 = trustData.v03;
  const v02 = trustData.v02;

  return (
    <section>
      <div className="flex flex-col justify-between gap-5 border-b border-[#DDE4DF] pb-7 lg:flex-row">
        <div>
          <p className="text-xs font-bold tracking-[0.15em] text-[#4C987C]">
            TRUST CENTER
          </p>

          <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] text-[#17211D] md:text-5xl">
            모델 신뢰와 로드맵
          </h1>

          <p className="mt-4 max-w-3xl leading-7 text-[#68736D]">
            성능 지표와 검증 구조를 공개하고, 아직 지원하지 않는 기능은
            상태를 함께 표시합니다.
          </p>
        </div>

        <div className="lg:text-right">
          <DataModeBadge />

          <p className="mt-2 text-xs text-[#68736D]">
            {trustData.validationPeriod} 검증 기준
          </p>
        </div>
      </div>

      <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="검토 대상"
          value={`${operationsSummary.targetUsers.toLocaleString()}명`}
          note={`전체 ${operationsSummary.totalReviewers.toLocaleString()}명 중 상위 20%`}
        />
        <MetricCard
          label="정밀도"
          value={percent(operationsSummary.precision)}
          note={`${operationsSummary.capturedUsers.toLocaleString()}명 상태 상실 포착 · 상위 20% 검토 대상 기준`}
          good
        />
        <MetricCard
          label="재현율"
          value={percent(operationsSummary.recall)}
          note={`최대 ${percent(operationsSummary.recallCeiling)}까지 가능`}
        />
        <MetricCard
          label="Lift"
          value={`${operationsSummary.lift.toFixed(2)}배`}
          note="무작위 선택 대비"
        />
      </div>

      <div className="mt-9 flex overflow-x-auto border-b border-[#DDE4DF]">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={[
              "min-w-40 whitespace-nowrap border-b-2 px-5 py-3 text-sm font-bold transition",
              activeTab === tab.key
                ? "border-[#137A5A] text-[#137A5A]"
                : "border-transparent text-[#68736D]",
            ].join(" ")}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {activeTab === "performance" && (
          <div className="grid gap-6">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Macro F1" value={overall.macroF1.toFixed(3)} />
              <MetricCard
                label="Macro PR-AUC"
                value={overall.macroPrAuc.toFixed(3)}
              />
              <MetricCard
                label="Macro ROC-AUC"
                value={overall.macroRocAuc.toFixed(3)}
              />
              <MetricCard
                label="Balanced Accuracy"
                value={overall.balancedAccuracy.toFixed(3)}
              />
            </div>

            <Panel
              title="클래스별 성능"
              description="세 가지 리텐션 상태를 각각 얼마나 잘 구분하는지 표시합니다."
            >
              <ClassPerformanceChart data={classPerformance} />
              <ClassPerformanceTable data={classPerformance} />
            </Panel>

            <Panel
              title="혼동 행렬"
              description="실제 상태와 모델 판단이 어긋나는 지점을 확인합니다."
            >
              <ConfusionMatrix rows={confusionMatrix} />
            </Panel>

            <Panel
              title="Top-K 성능"
              description="검토 용량을 늘릴수록 정밀도와 재현율이 어떻게 교환되는지 표시합니다."
            >
              <MulticlassTopKChart data={topK} />
            </Panel>

            {v03?.available && (
              <Expander
                title="v03 비교 기준 (3클래스 이전 코호트, 참고용)"
                caption={`v03은 2017년 후보 선정 → 2018년 활동 관찰 → 2019년 실제 상태 검증 구조를 사용한 이전 3클래스 모델입니다. ${trustData.modelVersion} 운영 화면의 기본 수치로 혼합하지 않습니다.`}
              >
                <div className="grid gap-6">
                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <MetricCard
                      label="Macro F1"
                      value={v03.overall.macroF1.toFixed(3)}
                      note="v03 Test · 3클래스 평균 F1"
                    />
                    <MetricCard
                      label="Macro PR-AUC"
                      value={v03.overall.macroPrAuc.toFixed(3)}
                      note="v03 Test · 불균형 데이터 핵심 지표"
                    />
                    <MetricCard
                      label="Macro ROC-AUC"
                      value={v03.overall.macroRocAuc.toFixed(3)}
                      note="v03 Test · 전체 순위 구분 성능"
                    />
                    <MetricCard
                      label="Test 표본"
                      value={`${v03.validationSamples.toLocaleString()}명`}
                      note="v03 이전 코호트"
                    />
                  </div>

                  <ClassPerformanceChart data={v03.classPerformance} />

                  {v03.confusionMatrix.length > 0 && (
                    <ConfusionMatrix rows={v03.confusionMatrix} />
                  )}

                  {v03.topK.length > 0 && (
                    <>
                      <MulticlassTopKChart data={v03.topK} />

                      {v03.top20 && (
                        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
                          <MetricCard
                            label="상위 20%"
                            value={`${v03.top20.targetUsers.toLocaleString()}명`}
                            note="v03 검토 인원"
                          />
                          <MetricCard
                            label="지위 상실 포착"
                            value={`${v03.top20.captured.toLocaleString()}명`}
                            note="약화·중단 실제 결과"
                          />
                          <MetricCard
                            label="Precision"
                            value={percent(v03.top20.precision)}
                            note="v03 상위 20%"
                          />
                          <MetricCard
                            label="Recall"
                            value={percent(v03.top20.recall)}
                            note="v03 상위 20%"
                          />
                          <MetricCard
                            label="Lift"
                            value={`${v03.top20.lift.toFixed(2)}배`}
                            note="v03 무작위 대비"
                          />
                        </div>
                      )}
                    </>
                  )}
                </div>
              </Expander>
            )}

            {v02?.available && (
              <Expander
                title="v02 비교 기준 (이진 이탈 모델, 참고용)"
                caption={`v02는 완전 이탈(churn)만을 이진 분류한 이전 세대 모델입니다. ${trustData.modelVersion} 운영 화면의 기본 수치로 혼합하지 않습니다.`}
              >
                <div className="grid gap-6">
                  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <MetricCard
                      label="PR-AUC"
                      value={v02.overall.prAuc.toFixed(3)}
                      note="v02 Test · 불균형 데이터 핵심 지표"
                    />
                    <MetricCard
                      label="ROC-AUC"
                      value={v02.overall.rocAuc.toFixed(3)}
                      note="v02 Test · 전체 순위 구분 성능"
                    />
                    <MetricCard
                      label="Recall"
                      value={percent(v02.overall.recall)}
                      note="v02 Test · 전체 이탈자 포착률"
                    />
                    <MetricCard
                      label="Precision"
                      value={percent(v02.overall.precision)}
                      note="v02 Test · 선별 대상 내 실제 이탈"
                    />
                  </div>

                  {v02.datasetComparison.length > 0 && (
                    <ModelComparisonChart data={v02.datasetComparison} />
                  )}

                  {v02.topK.length > 0 && (
                    <>
                      <BinaryTopKChart data={v02.topK} />
                      <BinaryTopKTable data={v02.topK} />
                    </>
                  )}
                </div>
              </Expander>
            )}
          </div>
        )}

        {activeTab === "split" && (
          <div className="grid gap-6">
            <Panel
              title="시간 분할 구조"
              description="과거 활동으로 피처를 만들고, 이후 연도의 실제 상태로 검증합니다."
            >
              <div className="grid gap-4 sm:grid-cols-3">
                {[
                  {
                    year: operationsSummary.targetYear - 2,
                    title: "비교",
                    detail: "직전 활동과의 변화량 계산 기준",
                  },
                  {
                    year: operationsSummary.targetYear - 1,
                    title: "선정·피처 마감",
                    detail: "여기까지의 활동만 모델 입력으로 사용",
                  },
                  {
                    year: operationsSummary.targetYear,
                    title: "실제 상태 검증",
                    detail: "학습에 쓰지 않고 결과 확인에만 사용",
                  },
                ].map((item) => (
                  <div
                    key={item.year}
                    className="rounded-xl border border-[#DDE4DF] bg-white p-5"
                  >
                    <p className="text-2xl font-bold text-[#137A5A]">
                      {item.year}
                    </p>
                    <p className="mt-2 font-bold text-[#17211D]">
                      {item.title}
                    </p>
                    <p className="mt-1 text-sm text-[#68736D]">
                      {item.detail}
                    </p>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel
              title="누수 방지 원칙"
              description="검증 결과가 과장되지 않도록 지키는 제약입니다."
            >
              <div className="grid gap-4 sm:grid-cols-2">
                {leakagePrinciples.map((item) => (
                  <StatusCard key={item.title} {...item} />
                ))}
              </div>
            </Panel>
          </div>
        )}

        {activeTab === "features" && (
          <div className="grid gap-6">
            <Panel
              title="피처 그룹 중요도"
              description={`Permutation importance · 기준 Macro PR-AUC ${trustData.baselinePrAuc.toFixed(3)}`}
            >
              <GroupImportanceChart data={trustData.groupImportance} />
            </Panel>

            <Panel
              title="상위 피처 중요도"
              description="개별 피처를 섞었을 때 Macro PR-AUC가 떨어지는 정도입니다."
            >
              <FeatureImportanceTable data={trustData.featureImportance} />
            </Panel>

            {v03?.available &&
              (v03.featureImportance.length > 0 ||
                v03.groupImportance.length > 0) && (
                <Expander
                  title="v03 비교 기준 (3클래스 이전 코호트, 참고용)"
                  caption="v03 최종 Test 4,157명의 Permutation 중요도입니다. 기준 Macro PR-AUC는 0.5986이며, v04 기본 중요도와 혼합하지 않는 이전 코호트 비교 자료입니다."
                >
                  <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
                    <FeatureImportanceTable data={v03.featureImportance} />
                    <GroupImportanceChart data={v03.groupImportance} />
                  </div>
                </Expander>
              )}

            {v02?.available &&
              (v02.featureImportance.length > 0 ||
                v02.groupImportance.length > 0) && (
                <Expander
                  title="v02 비교 기준 (이진 이탈 모델, 참고용)"
                  caption={`v02는 완전 이탈만 예측하는 이전 세대 모델의 중요도입니다. ${trustData.modelVersion} 기본 중요도와 혼합하지 않는 과거 비교 자료입니다.`}
                >
                  <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
                    <FeatureImportanceTable data={v02.featureImportance} />
                    <GroupImportanceChart data={v02.groupImportance} />
                  </div>
                </Expander>
              )}

            <Panel
              title="개인별 설명 범위"
              description="어디까지 개인 단위로 설명할 수 있는지 표시합니다."
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <StatusCard
                  title="행동 변화 비교"
                  description="비교 연도와 선정 연도의 활동량 차이"
                  status="현재 사용 가능"
                />
                <StatusCard
                  title="규칙 기반 근거"
                  description="관찰 가능한 신호를 심각도 순으로 제시"
                  status="규칙 기반 프로토타입"
                />
                <StatusCard
                  title="개인별 SHAP"
                  description="개별 예측에 대한 피처 기여도"
                  status="고도화 예정"
                />
                <StatusCard
                  title="보정 확률"
                  description="클래스 점수를 실제 확률로 변환"
                  status="고도화 예정"
                />
              </div>
            </Panel>
          </div>
        )}

        {activeTab === "roadmap" && (
          <Panel
            title="제품 상태와 로드맵"
            description="화면이 제공하는 기능과, 아직 데이터가 필요한 기능을 함께 표시합니다."
          >
            <div className="grid gap-4 sm:grid-cols-2">
              {productRoadmap.map((item) => (
                <div
                  key={item.title}
                  className="rounded-xl border border-[#DDE4DF] bg-white p-5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="font-bold text-[#17211D]">{item.title}</p>
                    <span className="whitespace-nowrap rounded bg-[#F1F4F1] px-2 py-1 text-xs text-[#68736D]">
                      {item.status}
                    </span>
                  </div>

                  <p className="mt-3 text-sm text-[#68736D]">
                    <span className="text-[#17211D]">필요 데이터 · </span>
                    {item.need}
                  </p>

                  <p className="mt-1 text-sm text-[#68736D]">
                    <span className="text-[#17211D]">운영 가치 · </span>
                    {item.value}
                  </p>
                </div>
              ))}
            </div>
          </Panel>
        )}
      </div>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs text-[#68736D]">
        Reviewer Retention · {operationsSummary.dataModeLabel} data ·{" "}
        {trustData.modelVersion} 최종 테스트 결과 기준
      </footer>
    </section>
  );
}

function ConfusionMatrix({ rows }) {
  const order = ["retained", "weakened", "stopped"];
  const lookup = new Map(
    rows.map((row) => [`${row.actual}|${row.predicted}`, row.users]),
  );
  const maximum = Math.max(...rows.map((row) => row.users), 1);

  return (
    <div className="overflow-x-auto">
      <table className="min-w-[520px] text-sm">
        <thead>
          <tr className="text-xs text-[#68736D]">
            <th className="py-2 pr-4 text-left">실제 \ 예측</th>
            {order.map((key) => (
              <th key={key} className="py-2 pr-4 text-left">
                {stateLabels[key]}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {order.map((actual) => (
            <tr key={actual} className="border-t border-[#DDE4DF]">
              <td className="py-2 pr-4 text-[#17211D]">
                {stateLabels[actual]}
              </td>

              {order.map((predicted) => {
                const users = lookup.get(`${actual}|${predicted}`) ?? 0;
                const isDiagonal = actual === predicted;

                return (
                  <td key={predicted} className="py-2 pr-4">
                    <span
                      className={[
                        "inline-flex min-w-16 justify-center rounded px-2 py-1",
                        isDiagonal
                          ? "font-bold text-[#137A5A]"
                          : "text-[#68736D]",
                      ].join(" ")}
                      style={{
                        backgroundColor: isDiagonal
                          ? `rgba(19, 122, 90, ${0.08 + (users / maximum) * 0.22})`
                          : `rgba(225, 93, 71, ${(users / maximum) * 0.18})`,
                      }}
                    >
                      {users.toLocaleString()}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Shared by the v04 headline panel and the v03 reference expander — both are
// 3-class models with the same classPerformance shape.
function ClassPerformanceChart({ data }) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid stroke="#E6EBE7" strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="className"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#68736D", fontSize: 12 }}
          />
          <YAxis
            domain={[0, 1]}
            axisLine={false}
            tickLine={false}
            width={40}
            tick={{ fill: "#68736D", fontSize: 12 }}
          />
          <Tooltip formatter={(value) => Number(value).toFixed(3)} />
          <Legend />
          <Bar dataKey="precision" name="정밀도" fill="#137A5A" radius={[5, 5, 0, 0]} />
          <Bar dataKey="recall" name="재현율" fill="#8BBBA6" radius={[5, 5, 0, 0]} />
          <Bar dataKey="prAuc" name="PR-AUC" fill="#B8C0BB" radius={[5, 5, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function ClassPerformanceTable({ data }) {
  return (
    <div className="mt-4 overflow-x-auto">
      <table className="min-w-[560px] text-sm">
        <thead>
          <tr className="text-left text-xs text-[#68736D]">
            <th className="py-2 pr-4">상태</th>
            <th className="py-2 pr-4">정밀도</th>
            <th className="py-2 pr-4">재현율</th>
            <th className="py-2 pr-4">F1</th>
            <th className="py-2">표본</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr key={item.className} className="border-t border-[#DDE4DF]">
              <td className="py-2 pr-4 text-[#17211D]">{item.className}</td>
              <td className="py-2 pr-4">{percent(item.precision)}</td>
              <td className="py-2 pr-4">{percent(item.recall)}</td>
              <td className="py-2 pr-4">{item.f1.toFixed(3)}</td>
              <td className="py-2">{item.support.toLocaleString()}명</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// 3-class Top-K (status-loss capture) — shared by v04 and the v03 reference.
function MulticlassTopKChart({ data }) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data.map((item) => ({
            ...item,
            label: percent(item.targetRate, 0),
          }))}
        >
          <CartesianGrid stroke="#E6EBE7" strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="label"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#68736D", fontSize: 12 }}
          />
          <YAxis
            domain={[0, 1]}
            axisLine={false}
            tickLine={false}
            width={40}
            tick={{ fill: "#68736D", fontSize: 12 }}
          />
          <Tooltip formatter={(value) => percent(Number(value))} />
          <Legend />
          <Line type="monotone" dataKey="precision" name="정밀도" stroke="#137A5A" strokeWidth={3} />
          <Line type="monotone" dataKey="recall" name="재현율" stroke="#A66A18" strokeWidth={3} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// v02's Validation-vs-Test comparison across five raw metrics (core.charts
// model_comparison) — v02 is binary, so this has no v04/v03 equivalent.
function ModelComparisonChart({ data }) {
  const metrics = [
    { key: "precision", label: "정밀도" },
    { key: "recall", label: "재현율" },
    { key: "f1", label: "F1" },
    { key: "rocAuc", label: "ROC-AUC" },
    { key: "prAuc", label: "PR-AUC" },
  ];
  const long = metrics.map(({ key, label }) => {
    const row = { metric: label };
    data.forEach((item) => {
      row[item.dataset] = item[key];
    });
    return row;
  });

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={long}>
          <CartesianGrid stroke="#E6EBE7" strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="metric"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#68736D", fontSize: 12 }}
          />
          <YAxis
            domain={[0, 1]}
            axisLine={false}
            tickLine={false}
            width={40}
            tick={{ fill: "#68736D", fontSize: 12 }}
          />
          <Tooltip formatter={(value) => Number(value).toFixed(3)} />
          <Legend />
          <Bar dataKey="Validation" fill="#D9A441" radius={[5, 5, 0, 0]} />
          <Bar dataKey="Test" fill="#137A5A" radius={[5, 5, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

// v02's Top-K uses churn-specific field names (target_rate_pct, precision_at_k,
// …) instead of the 3-class status-loss schema, so it gets its own chart.
function BinaryTopKChart({ data }) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid stroke="#E6EBE7" strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="targetRatePercent"
            unit="%"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#68736D", fontSize: 12 }}
          />
          <YAxis
            domain={[0, 1]}
            axisLine={false}
            tickLine={false}
            width={40}
            tick={{ fill: "#68736D", fontSize: 12 }}
          />
          <Tooltip formatter={(value) => percent(Number(value))} />
          <Legend />
          <Line type="monotone" dataKey="precision" name="정밀도" stroke="#137A5A" strokeWidth={3} />
          <Line type="monotone" dataKey="recall" name="재현율" stroke="#A66A18" strokeWidth={3} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function BinaryTopKTable({ data }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-[620px] text-sm">
        <thead>
          <tr className="text-left text-xs text-[#68736D]">
            <th className="py-2 pr-4">검토 비율</th>
            <th className="py-2 pr-4">검토 인원</th>
            <th className="py-2 pr-4">포착 이탈자</th>
            <th className="py-2 pr-4">Precision@K</th>
            <th className="py-2 pr-4">Recall@K</th>
            <th className="py-2">Lift@K</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr key={item.targetRatePercent} className="border-t border-[#DDE4DF]">
              <td className="py-2 pr-4 text-[#17211D]">
                {item.targetRatePercent.toFixed(0)}%
              </td>
              <td className="py-2 pr-4">{item.targetUsers.toLocaleString()}명</td>
              <td className="py-2 pr-4">
                {item.capturedChurnUsers.toLocaleString()}명
              </td>
              <td className="py-2 pr-4">{percent(item.precision)}</td>
              <td className="py-2 pr-4">{percent(item.recall)}</td>
              <td className="py-2">{item.lift.toFixed(2)}×</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Shared by the v04 headline panel and the v03/v02 reference expanders.
function GroupImportanceChart({ data }) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical">
          <CartesianGrid stroke="#E6EBE7" strokeDasharray="4 4" horizontal={false} />
          <XAxis
            type="number"
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#68736D", fontSize: 12 }}
          />
          <YAxis
            type="category"
            dataKey="group"
            width={90}
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#68736D", fontSize: 12 }}
          />
          <Tooltip formatter={(value) => Number(value).toFixed(4)} />
          <Bar dataKey="importance" name="중요도" fill="#137A5A" radius={[0, 5, 5, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function FeatureImportanceTable({ data }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-[620px] text-sm">
        <thead>
          <tr className="text-left text-xs text-[#68736D]">
            <th className="py-2 pr-4">순위</th>
            <th className="py-2 pr-4">피처</th>
            <th className="py-2 pr-4">그룹</th>
            <th className="py-2 pr-4">중요도</th>
            <th className="py-2">기여 비율</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr key={item.feature} className="border-t border-[#DDE4DF]">
              <td className="py-2 pr-4 text-[#68736D]">{item.rank}</td>
              <td className="py-2 pr-4 font-mono text-xs text-[#17211D]">
                {item.feature}
              </td>
              <td className="py-2 pr-4 text-[#68736D]">{item.group}</td>
              <td className="py-2 pr-4">{item.importance.toFixed(4)}</td>
              <td className="py-2">{item.sharePercent.toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Mirrors Streamlit's collapsed-by-default st.expander for the v02/v03
// reference sections (views/trust_center.py) — closed until the operator
// asks for the historical comparison.
function Expander({ title, caption, children }) {
  return (
    <details className="group rounded-xl border border-[#DDE4DF] bg-white">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-6 py-4 font-bold text-[#17211D]">
        <span className="flex items-center gap-2">
          <span className="text-[#68736D]">🕘</span>
          {title}
        </span>
        <span className="text-xs font-normal text-[#68736D] transition group-open:rotate-180">
          ▾
        </span>
      </summary>

      <div className="border-t border-[#DDE4DF] p-6">
        {caption && (
          <p className="mb-5 text-xs leading-5 text-[#68736D]">{caption}</p>
        )}
        {children}
      </div>
    </details>
  );
}

function Panel({ title, description, children }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-6">
      <h2 className="text-lg font-bold text-[#17211D]">{title}</h2>
      <p className="mt-2 text-sm text-[#68736D]">{description}</p>
      <div className="mt-5">{children}</div>
    </div>
  );
}

function StatusCard({ title, description, status }) {
  return (
    <div className="rounded-xl bg-[#F7F8F5] p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="font-bold text-[#17211D]">{title}</p>
        <span className="whitespace-nowrap rounded bg-white px-2 py-1 text-xs text-[#68736D]">
          {status}
        </span>
      </div>
      <p className="mt-2 text-sm text-[#68736D]">{description}</p>
    </div>
  );
}

function MetricCard({ label, value, note, good = false }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white px-5 py-4">
      <p className="text-sm text-[#68736D]">{label}</p>

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

export default TrustCenterPage;
