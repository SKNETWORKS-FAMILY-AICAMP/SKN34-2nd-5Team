import { useEffect, useState } from "react";
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
import PageHeader from "../components/common/PageHeader";
import Skeleton from "../components/common/Skeleton";
import ErrorState from "../components/common/ErrorState";
import ReviewCapacityDial from "../components/trust/ReviewCapacityDial";
import { useOperationsSummary } from "../context/operations-context";
import { loadTrustData } from "../data";

const tabs = [
  { key: "performance", label: "성능과 Top-K" },
  { key: "split", label: "시간 분할·누수 방지" },
  { key: "features", label: "피처 근거" },
  { key: "scope", label: "적용 범위" },
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

// What the product covers and where its boundary is — a spec, not a
// to-do list. Each entry states what IS true today; "제공하지 않는 것"
// entries explain the boundary rather than promising a future date.
const scopeProvided = [
  {
    title: "운영 홈 · 검토 큐",
    description: "Signal Atlas로 오늘 먼저 볼 대상을 발견하고 큐로 이동합니다.",
  },
  {
    title: "리뷰어 검토",
    description: "근거 확인부터 판단 저장까지 목록을 떠나지 않고 처리합니다.",
  },
  {
    title: "위험 유형 플레이북",
    description: "규칙 기반 위험 유형별 대응 전략과 대상 명단 저장을 제공합니다.",
  },
  {
    title: "지역 콘텐츠 위험",
    description: "권역 단위 공급 위험 비교와 도시 위치 모식도를 제공합니다.",
  },
];

const scopeNotProvided = [
  {
    title: "캠페인 발송·복귀 성과 추적",
    description:
      "실제 개입이 일어난 적이 없어 만들 수 없습니다. 대상 명단 저장까지가 이 서비스의 범위입니다.",
  },
  {
    title: "개인별 SHAP · 보정 확률",
    description:
      "관찰된 활동 변화와 규칙 기반 근거는 제공하지만, 개별 예측의 피처 기여도나 실제 확률로 보정된 점수는 제공하지 않습니다.",
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
  const operationsSummary = useOperationsSummary();
  const [activeTab, setActiveTab] = useState("performance");
  const [trustData, setTrustData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    loadTrustData()
      .then((data) => {
        if (!cancelled) setTrustData(data);
      })
      .catch((loadError) => {
        if (!cancelled) setError(loadError.message);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <ErrorState message={error} />;
  }

  if (!trustData) {
    return <Skeleton rows={4} columns={4} />;
  }

  const { overall, classPerformance, confusionMatrix, topK } = trustData;
  const v03 = trustData.v03;
  const v02 = trustData.v02;

  return (
    <section>
      <PageHeader
        title="모델 신뢰"
        description="성능 지표와 검증 구조를 공개하고, 모델이 무엇에 대해 검증됐는지 적용 범위를 함께 밝힙니다."
        meta={
          <>
            <DataModeBadge />
            <p className="mt-2 text-xs text-[#626D67]">
              {trustData.validationPeriod} 검증 기준
            </p>
          </>
        }
      />

      <div className="mt-4">
        <ReviewCapacityDial
          topK={topK}
          currentTargetRate={operationsSummary.targetUsers / operationsSummary.totalReviewers}
        />
      </div>

      <div className="mt-7 flex overflow-x-auto border-b border-[#DDE4DF]">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={[
              "min-w-40 whitespace-nowrap border-b-2 px-5 py-3 text-sm font-bold transition",
              activeTab === tab.key
                ? "border-[#137A5A] text-[#137A5A]"
                : "border-transparent text-[#626D67]",
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
                    <p className="mt-1 text-sm text-[#626D67]">
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
              description="관찰된 활동 변화와 규칙 기반 근거를 개인 단위로 제시합니다. 개별 예측에 대한 피처 기여도(SHAP)나 보정 확률은 제공하지 않습니다."
            >
              <div className="grid gap-3 sm:grid-cols-2">
                <ScopeCard title="행동 변화 비교" description="비교 연도와 선정 연도의 활동량 차이" covered />
                <ScopeCard title="규칙 기반 근거" description="관찰 가능한 신호를 심각도 순으로 제시" covered />
              </div>
            </Panel>
          </div>
        )}

        {activeTab === "scope" && (
          <div className="grid gap-6">
            <Panel
              title="제공하는 것"
              description="현재 화면에서 실제로 동작하는 기능입니다."
            >
              <div className="grid gap-3 sm:grid-cols-2">
                {scopeProvided.map((item) => (
                  <ScopeCard key={item.title} {...item} covered />
                ))}
              </div>
            </Panel>

            <Panel
              title="제공하지 않는 것"
              description="약속이 아니라 경계입니다 — 왜 안 되는지를 함께 적습니다."
            >
              <div className="grid gap-3 sm:grid-cols-2">
                {scopeNotProvided.map((item) => (
                  <ScopeCard key={item.title} {...item} />
                ))}
              </div>
            </Panel>

            <Panel
              title="데이터 커버리지"
              description="Yelp Open Dataset이 실제로 포함하는 지역입니다."
            >
              <p className="text-sm leading-6 text-[#626D67]">
                14개 권역(필라델피아·탬파·내슈빌 등 특정 대도시권)에서 활동한
                파워 리뷰어를 대상으로 학습·검증했습니다. 다른 지역 리뷰어에
                대한 일반화는 검증되지 않았습니다.
              </p>
            </Panel>
          </div>
        )}
      </div>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs text-[#626D67]">
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
          <tr className="text-xs text-[#626D67]">
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
                          : "text-[#626D67]",
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
            tick={{ fill: "#626D67", fontSize: 12 }}
          />
          <YAxis
            domain={[0, 1]}
            axisLine={false}
            tickLine={false}
            width={40}
            tick={{ fill: "#626D67", fontSize: 12 }}
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
          <tr className="text-left text-xs text-[#626D67]">
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
            tick={{ fill: "#626D67", fontSize: 12 }}
          />
          <YAxis
            domain={[0, 1]}
            axisLine={false}
            tickLine={false}
            width={40}
            tick={{ fill: "#626D67", fontSize: 12 }}
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
            tick={{ fill: "#626D67", fontSize: 12 }}
          />
          <YAxis
            domain={[0, 1]}
            axisLine={false}
            tickLine={false}
            width={40}
            tick={{ fill: "#626D67", fontSize: 12 }}
          />
          <Tooltip formatter={(value) => Number(value).toFixed(3)} />
          <Legend />
          <Bar dataKey="Validation" fill="#A66A18" radius={[5, 5, 0, 0]} />
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
            tick={{ fill: "#626D67", fontSize: 12 }}
          />
          <YAxis
            domain={[0, 1]}
            axisLine={false}
            tickLine={false}
            width={40}
            tick={{ fill: "#626D67", fontSize: 12 }}
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
          <tr className="text-left text-xs text-[#626D67]">
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
            tick={{ fill: "#626D67", fontSize: 12 }}
          />
          <YAxis
            type="category"
            dataKey="group"
            width={90}
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#626D67", fontSize: 12 }}
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
          <tr className="text-left text-xs text-[#626D67]">
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
              <td className="py-2 pr-4 text-[#626D67]">{item.rank}</td>
              <td className="py-2 pr-4 font-mono text-xs text-[#17211D]">
                {item.feature}
              </td>
              <td className="py-2 pr-4 text-[#626D67]">{item.group}</td>
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
          <span className="text-[#626D67]">🕘</span>
          {title}
        </span>
        <span className="text-xs font-normal text-[#626D67] transition group-open:rotate-180">
          ▾
        </span>
      </summary>

      <div className="border-t border-[#DDE4DF] p-6">
        {caption && (
          <p className="mb-5 text-xs leading-5 text-[#626D67]">{caption}</p>
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
      <p className="mt-2 text-sm text-[#626D67]">{description}</p>
      <div className="mt-5">{children}</div>
    </div>
  );
}

// Scope boundary indicator — a checkmark/dash pair, not a status badge that
// reads as a promised delivery date. "covered" cards say what works;
// uncovered cards explain the boundary in the description itself.
function ScopeCard({ title, description, covered = false }) {
  return (
    <div className="rounded-lg border border-[#DDE4DF] bg-white p-4">
      <div className="flex items-start gap-2">
        <span
          className={covered ? "text-[#137A5A]" : "text-[#B3BBB6]"}
          aria-hidden="true"
        >
          {covered ? "✓" : "—"}
        </span>
        <p className="text-sm font-medium text-[#17211D]">{title}</p>
      </div>
      <p className="mt-1.5 pl-5 text-xs leading-5 text-[#626D67]">
        {description}
      </p>
    </div>
  );
}

function StatusCard({ title, description, status }) {
  return (
    <div className="rounded-xl bg-[#F7F8F5] p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="font-bold text-[#17211D]">{title}</p>
        <span className="whitespace-nowrap rounded bg-white px-2 py-1 text-xs text-[#626D67]">
          {status}
        </span>
      </div>
      <p className="mt-2 text-sm text-[#626D67]">{description}</p>
    </div>
  );
}

function MetricCard({ label, value, note, good = false }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white px-5 py-4">
      <p className="text-sm text-[#626D67]">{label}</p>

      <p
        className={[
          "mt-2 text-2xl font-bold",
          good ? "text-[#137A5A]" : "text-[#17211D]",
        ].join(" ")}
      >
        {value}
      </p>

      {note && <p className="mt-1 text-xs text-[#626D67]">{note}</p>}
    </div>
  );
}

export default TrustCenterPage;
