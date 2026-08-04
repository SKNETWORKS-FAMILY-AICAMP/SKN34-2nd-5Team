import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import ErrorState from "../components/common/ErrorState";
import Skeleton from "../components/common/Skeleton";
import { useOperationsSummary } from "../context/operations-context";
import { loadTrustData } from "../data";

const STATUS_LABELS = {
  operational: "운영 중",
  candidate: "비교 후보",
  archived: "과거 참고",
};

// Identity color for the 3 outcome classes — same hexes ReviewerScoreBars.jsx
// already uses on Reviewer 360, kept consistent so "유지/약화/중단" always
// means the same color everywhere in the app.
const CLASS_COLORS = {
  "파워 지위 유지": "#137A5A",
  "파워 지위 약화": "#D48A43",
  "리뷰 활동 중단": "#E15D47",
};
const CLASS_ORDER = ["파워 지위 유지", "파워 지위 약화", "리뷰 활동 중단"];
const CLASS_SHORT_LABELS = {
  retained: "유지",
  weakened: "약화",
  stopped: "중단",
};

// Feature-group identity color — deliberately NOT the class colors above
// (grouping by feature type is a different categorical dimension than the
// outcome classes; reusing the same hues would visually imply a relationship
// that doesn't exist). First 3 slots of the dataviz skill's validated
// 8-color categorical theme, which clears CVD separation for all 3 pairs.
const GROUP_COLORS = {
  "작성 간격": "#2a78d6",
  "리뷰 활동량": "#eb6834",
  "음식점 탐색": "#1baf7a",
};

// Sequential ramp (skill default: blue, light→dark) for the confusion-matrix
// heatmap — magnitude only, deliberately not the status green/red used
// elsewhere so cell shade never reads as "good/bad performance."
const HEATMAP_STEPS = ["#e8f0fb", "#b7d3f6", "#6da7ec", "#2a78d6", "#184f95"];

function heatmapColor(value, max) {
  if (max <= 0) return HEATMAP_STEPS[0];
  const ratio = Math.min(1, value / max);
  const index = Math.min(HEATMAP_STEPS.length - 1, Math.round(ratio * (HEATMAP_STEPS.length - 1)));
  return HEATMAP_STEPS[index];
}

const LIMITATIONS = [
  {
    title: "모델 점수는 순위이지 이탈 확률이 아닙니다.",
    description: "점수는 상대적 운영 우선순위를 의미하며 절대적인 발생 확률로 해석할 수 없습니다.",
  },
  {
    title: "위치는 거주지가 아닌 공개 음식점 리뷰 활동 기준입니다.",
    description: "리뷰어가 공개적으로 리뷰한 음식점의 위치를 집계하며 실제 거주지나 이동 경로를 뜻하지 않습니다.",
  },
  {
    title: "2019년 결과는 2018년 운영 시점에 사용되지 않았습니다.",
    description: "2019년 데이터는 실제 상태 라벨과 사후 검증에만 사용해 시간 누수를 방지했습니다.",
  },
  {
    title: "개입 효과는 측정되기 전까지 가설입니다.",
    description: "추천 운영안의 효과는 저장만으로 확정되지 않으며 실행 이후 측정 데이터로 검증해야 합니다.",
  },
];

function percent(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${(Number(value) * 100).toFixed(digits)}%`;
}

function number(value) {
  return Number(value ?? 0).toLocaleString();
}

function getSnapshotData(trustData, version) {
  if (version === "v05_05_dl") {
    return {
      available: true,
      overall: trustData.overall,
      classPerformance: trustData.classPerformance,
      confusionMatrix: trustData.confusionMatrix,
      topK: trustData.topK,
      groupImportance: trustData.groupImportance,
      featureImportance: trustData.featureImportance,
      binary: false,
    };
  }

  if (version === "v04") return { ...trustData.v04, binary: false };
  if (version === "v05_ml_xgb") return { ...trustData.v05MlXgb, binary: false };
  if (version === "v03") return { ...trustData.v03, binary: false };
  if (version === "v02") return { ...trustData.v02, binary: true };
  return { available: false };
}

function findCapacityPoint(snapshotData, targetRate) {
  if (!snapshotData?.topK?.length) return null;
  return (
    snapshotData.topK.find((item) => {
      const itemRate = snapshotData.binary
        ? item.targetRatePercent / 100
        : item.targetRate;
      return Math.abs(itemRate - targetRate) < 0.001;
    }) ?? snapshotData.topK[0]
  );
}

function TrustCenterPage() {
  const operationsSummary = useOperationsSummary();
  const [trustData, setTrustData] = useState(null);
  const [error, setError] = useState(null);
  const [selectedVersion, setSelectedVersion] = useState("v05_05_dl");

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

  const selectedSnapshot = useMemo(
    () => trustData?.snapshots?.find((item) => item.modelVersion === selectedVersion),
    [selectedVersion, trustData],
  );
  const snapshotData = useMemo(
    () => (trustData ? getSnapshotData(trustData, selectedVersion) : null),
    [selectedVersion, trustData],
  );

  if (error) return <ErrorState message={error} />;
  if (!trustData) return <Skeleton rows={6} columns={4} />;

  const targetRate = selectedSnapshot?.priorityTargetRate ?? 0.2;
  const capacityPoint = findCapacityPoint(snapshotData, targetRate);
  const validationSamples =
    selectedSnapshot?.validationSamples ?? snapshotData?.validationSamples ?? 0;
  const targetUsers = capacityPoint
    ? capacityPoint.targetUsers
    : selectedVersion === "v05_05_dl"
      ? operationsSummary.targetUsers
      : 0;

  return (
    <section className="min-h-full bg-white pb-6 text-[#17211D]">
      <header className="flex flex-wrap items-end justify-end gap-4 border-b border-[#DDE4DF] pb-4">
        <label className="flex items-center gap-3 rounded-lg border border-[#DDE4DF] bg-white px-4 py-2 text-sm">
          <span className="font-bold text-[#626D67]">검증 스냅샷</span>
          <select
            value={selectedVersion}
            onChange={(event) => setSelectedVersion(event.target.value)}
            className="bg-transparent font-black outline-none"
          >
            {trustData.snapshots.map((snapshot) => (
              <option key={snapshot.modelVersion} value={snapshot.modelVersion}>
                {snapshot.modelVersion} · {STATUS_LABELS[snapshot.status]}
              </option>
            ))}
          </select>
        </label>
      </header>

      <div className="mt-4 grid grid-cols-2 overflow-hidden rounded-xl border border-[#DDE4DF] bg-white sm:grid-cols-4 lg:grid-cols-7">
        <SummaryItem label="서비스 버전" value={trustData.serviceVersion ?? "v05"} note="React 운영 화면" />
        <SummaryItem label="모델 버전" value={selectedSnapshot?.modelVersion ?? selectedVersion} note={STATUS_LABELS[selectedSnapshot?.status]} />
        <SummaryItem label="검증 표본" value={`${number(validationSamples)}명`} note={selectedSnapshot?.problemType} />
        <SummaryItem label="비교 기간" value={selectedSnapshot?.comparisonYear ?? "-"} />
        <SummaryItem label="선정·관찰 기간" value={selectedSnapshot?.selectionYear ?? "-"} />
        <SummaryItem label="검증 기간" value={selectedSnapshot?.validationYear ?? "-"} />
        <SummaryItem label="시간 누수" value="점검 완료" note="미래 정보 입력 제외" good />
      </div>

      <Panel className="mt-4" title="운영자가 반드시 알아야 할 한계" info="화면 수치를 판단에 사용할 때 항상 적용되는 원칙입니다.">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {LIMITATIONS.map((item, index) => (
            <div key={item.title} className="rounded-lg bg-[#F6F8F6] p-3">
              <span className="grid h-6 w-6 place-items-center rounded-full bg-[#EDF6F1] text-xs font-black text-[#087A5A]">
                {index + 1}
              </span>
              <p className="mt-2 text-sm font-black">{item.title}</p>
              <p className="mt-1 text-xs leading-5 text-[#626D67]">{item.description}</p>
            </div>
          ))}
        </div>
      </Panel>

      <div className="mt-4 grid gap-4">
          <Panel title="운영 용량과 우선 검토 범위" info="저장된 Top-K 검증 결과를 기준으로 표시합니다.">
            <CapacityBar total={validationSamples} target={targetUsers} rate={targetRate} />
            <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
              <SmallMetric label="검토 대상" value={`${number(targetUsers)}명`} />
              <SmallMetric
                label="Precision"
                value={capacityPoint ? percent(snapshotData.binary ? capacityPoint.precision : capacityPoint.precision) : "-"}
              />
              <SmallMetric
                label="Recall"
                value={capacityPoint ? percent(snapshotData.binary ? capacityPoint.recall : capacityPoint.recall) : "-"}
              />
              <SmallMetric label="Lift" value={capacityPoint ? `${capacityPoint.lift.toFixed(2)}배` : "-"} />
            </div>
            <p className="mt-3 text-xs leading-5 text-[#626D67]">
              {selectedVersion === "v05_05_dl"
                ? "현재 운영은 통합 위험 순위 상위 20%를 기본 검토 범위로 사용합니다."
                : selectedVersion === "v05_ml_xgb"
                  ? "XGBoost v05는 Trust Center 비교 후보이며 현재 운영 대상과 예측 결과를 바꾸지 않습니다."
                : "과거 스냅샷은 당시 저장된 평가 결과이며 현재 운영 대상과 혼합하지 않습니다."}
            </p>
          </Panel>

          <Panel title="모델 평가 요약" info="선택한 스냅샷의 최종 테스트 결과입니다.">
            {snapshotData.available ? (
              <>
                <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                  {snapshotData.binary ? (
                    <>
                      <SmallMetric label="PR-AUC" value={snapshotData.overall.prAuc.toFixed(3)} />
                      <SmallMetric label="ROC-AUC" value={snapshotData.overall.rocAuc.toFixed(3)} />
                      <SmallMetric label="Precision" value={percent(snapshotData.overall.precision)} />
                      <SmallMetric label="Recall" value={percent(snapshotData.overall.recall)} />
                    </>
                  ) : (
                    <>
                      <SmallMetric label="Macro F1" value={snapshotData.overall.macroF1.toFixed(3)} />
                      <SmallMetric label="Macro PR-AUC" value={snapshotData.overall.macroPrAuc.toFixed(3)} />
                      <SmallMetric label="Macro ROC-AUC" value={snapshotData.overall.macroRocAuc.toFixed(3)} />
                      <SmallMetric label="Balanced Accuracy" value={snapshotData.overall.balancedAccuracy.toFixed(3)} />
                    </>
                  )}
                </div>
                {!snapshotData.binary && snapshotData.classPerformance?.length > 0 && (
                  <ClassPerformanceChart classPerformance={snapshotData.classPerformance} />
                )}
              </>
            ) : (
              <EmptyState text="이 스냅샷의 평가 지표가 저장되어 있지 않습니다." />
            )}
          </Panel>

          {!snapshotData.binary && snapshotData.confusionMatrix?.length > 0 && (
            <Panel title="혼동 행렬" info="실제 상태(행) 대비 모델 예측(열)의 인원수입니다. 진하기는 인원수 크기이며 정오답 판단이 아닙니다.">
              <ConfusionMatrixHeatmap matrix={snapshotData.confusionMatrix} />
            </Panel>
          )}

          {!snapshotData.binary && snapshotData.groupImportance?.length > 0 && (
            <Panel title="주요 특징 그룹" info="Permutation importance 기반 사후 해석 결과입니다.">
              <div className="grid gap-3 md:grid-cols-3">
                {snapshotData.groupImportance.map((item) => (
                  <ImportanceRow key={item.group} item={item} data={snapshotData.groupImportance} />
                ))}
              </div>
              <p className="mt-3 text-xs leading-5 text-[#626D67]">
                막대 길이는 그룹 내 특징들의 permutation importance 합, 우측 숫자는 그룹에 속한 특징 개수입니다.
              </p>
            </Panel>
          )}

          {!snapshotData.binary && snapshotData.featureImportance?.length > 0 && (
            <Panel title="특징 중요도 (개별)" info="상위 개별 특징의 permutation importance이며 그룹 색으로 소속을 표시합니다.">
              <FeatureImportanceChart features={snapshotData.featureImportance} />
            </Panel>
          )}

          {trustData.v04?.available && trustData.overall && (
            <Panel title="버전 추세 (v04 → v05_05_dl)" info="같은 2018→2019 Test 6,533명 표본에서 이전 운영 모델(v04, 로지스틱)과 현재 운영 모델(v05_05_dl, Lifecycle Fusion H2 딥러닝)을 비교합니다.">
              <VersionTrend
                before={trustData.v04.overall}
                after={trustData.overall}
                beforeLabel="v04"
                afterLabel="v05_05_dl"
                beforeSnapshot={trustData.snapshots.find((item) => item.modelVersion === "v04")}
                afterSnapshot={trustData.snapshots.find((item) => item.modelVersion === "v05_05_dl")}
              />
            </Panel>
          )}
      </div>

      <Panel className="mt-4" title="데이터 계보 타임라인" info="선정 시점 이후 정보가 모델 입력에 섞이지 않도록 역할을 분리했습니다.">
        <DataLineageTimeline
          comparisonYear={selectedSnapshot?.comparisonYear}
          selectionYear={selectedSnapshot?.selectionYear}
          validationYear={selectedSnapshot?.validationYear}
        />
      </Panel>

      <Panel className="mt-4" title="검증 스냅샷" info="운영·비교 후보·과거 모델 결과를 조회하며 현재 운영 수치와 자동 합산하지 않습니다.">
        <div className="overflow-x-auto">
          <table className="min-w-[820px] w-full text-sm">
            <thead className="bg-[#F6F8F6] text-left text-xs text-[#626D67]">
              <tr>
                <th className="px-4 py-3">버전</th>
                <th className="px-4 py-3">상태</th>
                <th className="px-4 py-3">문제 유형</th>
                <th className="px-4 py-3">피처</th>
                <th className="px-4 py-3">선정 → 검증</th>
                <th className="px-4 py-3">검증 표본</th>
                <th className="px-4 py-3 text-right">조회</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E4E9E5]">
              {trustData.snapshots.map((snapshot) => (
                <tr key={snapshot.modelVersion} className={snapshot.modelVersion === selectedVersion ? "bg-[#EEF7F2]" : ""}>
                  <td className="px-4 py-3 font-black">{snapshot.modelVersion}</td>
                  <td className="px-4 py-3"><StatusBadge status={snapshot.status} /></td>
                  <td className="px-4 py-3 text-[#626D67]">{snapshot.problemType}</td>
                  <td className="px-4 py-3">
                    {snapshot.featureCount}개
                    {snapshot.featureSet && (
                      <span className="ml-1 text-[#8A948F]">({snapshot.featureSet})</span>
                    )}
                  </td>
                  <td className="px-4 py-3">{snapshot.selectionYear} → {snapshot.validationYear}</td>
                  <td className="px-4 py-3">{number(snapshot.validationSamples)}명</td>
                  <td className="px-4 py-3 text-right">
                    <button type="button" onClick={() => setSelectedVersion(snapshot.modelVersion)} className="font-black text-[#087A5A]">
                      {snapshot.modelVersion === selectedVersion ? "선택됨" : "결과 보기 →"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        <ReferenceCard title="코호트 정의">
          음식점 리뷰 10건 이상, 활동 월 3개월 이상을 충족한 선정 연도 파워 리뷰어를 기준으로 합니다.
        </ReferenceCard>
        <ReferenceCard title="시간 누수 방지">
          선정·피처 마감 이후의 리뷰와 상태 라벨은 모델 입력에서 제외하고 사후 검증에만 사용합니다.
        </ReferenceCard>
        <ReferenceCard title="모델 비교">
          v05_05_dl(Lifecycle Fusion H2)이 현재 3상태 운영 모델이며, v05_ml_xgb는 XGBoost 비교 후보입니다. v04·v03은 과거 3상태, v02는 이진 이탈 참고 모델입니다.
        </ReferenceCard>
        <ReferenceCard title="용어 사전">
          위험 점수는 확률이 아닌 우선순위이며 리뷰 활동 반경은 공개 음식점 리뷰 위치의 분포입니다.
        </ReferenceCard>
      </div>
    </section>
  );
}

function InfoTip({ text }) {
  return (
    <span className="group relative inline-flex" tabIndex={0}>
      <span className="grid h-5 w-5 cursor-help place-items-center rounded-full border border-[#AEB9B2] text-[11px] font-black text-[#626D67]">i</span>
      <span className="pointer-events-none absolute left-1/2 top-7 z-30 hidden w-72 -translate-x-1/2 rounded-lg bg-[#17211D] px-3 py-2 text-xs font-medium leading-5 text-white shadow-xl group-hover:block group-focus:block">
        {text}
      </span>
    </span>
  );
}

function SummaryItem({ label, value, note, good = false }) {
  return (
    <div className="min-h-[82px] border-b border-r border-[#DDE4DF] px-3 py-3 last:border-r-0 lg:border-b-0">
      <p className="text-[11px] font-bold text-[#626D67]">{label}</p>
      <p className={`mt-2 text-xl font-black ${good ? "text-[#087A5A]" : ""}`}>{value ?? "-"}</p>
      {note && <p className="mt-1 truncate text-[10px] text-[#7A8580]">{note}</p>}
    </div>
  );
}

function Panel({ title, info, className = "", children }) {
  return (
    <section className={`rounded-xl border border-[#DDE4DF] bg-white p-4 shadow-[0_3px_14px_rgba(23,33,29,0.025)] ${className}`}>
      <div className="flex items-center gap-2">
        <h2 className="text-base font-black">{title}</h2>
        {info && <InfoTip text={info} />}
      </div>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function CapacityBar({ total, target, rate }) {
  const safeRate = Math.max(0, Math.min(1, Number(rate ?? 0)));
  return (
    <div>
      <div className="flex justify-between text-xs text-[#626D67]"><span>0명</span><span>전체 {number(total)}명</span></div>
      <div className="relative mt-2 h-3 rounded-full bg-[#E8EDE9]">
        <span className="absolute inset-y-0 left-0 rounded-full bg-[#087A5A]" style={{ width: `${safeRate * 100}%` }} />
        <span className="absolute top-1/2 h-7 w-0.5 -translate-y-1/2 bg-[#17211D]" style={{ left: `${safeRate * 100}%` }} />
      </div>
      <p className="mt-3 text-center text-2xl font-black text-[#087A5A]">{number(target)}명 <span className="text-base">({percent(safeRate)})</span></p>
    </div>
  );
}

function SmallMetric({ label, value }) {
  return <div className="rounded-lg bg-[#F6F8F6] p-3"><p className="text-[11px] text-[#626D67]">{label}</p><p className="mt-1 text-lg font-black">{value}</p></div>;
}

function ClassPerformanceChart({ classPerformance }) {
  const metrics = [
    { key: "precision", label: "정밀도" },
    { key: "recall", label: "재현율" },
    { key: "f1", label: "F1" },
  ];
  const orderedClasses = CLASS_ORDER.filter((name) =>
    classPerformance.some((item) => item.className === name),
  );
  const chartData = metrics.map(({ key, label }) => {
    const row = { metric: label };
    classPerformance.forEach((item) => {
      row[item.className] = item[key];
    });
    return row;
  });

  return (
    <div className="mt-4 h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#E6EBE7" strokeDasharray="4 4" vertical={false} />
          <XAxis dataKey="metric" axisLine={false} tickLine={false} tick={{ fill: "#626D67", fontSize: 12 }} />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(value) => `${Math.round(value * 100)}%`}
            axisLine={false}
            tickLine={false}
            width={44}
            tick={{ fill: "#626D67", fontSize: 12 }}
          />
          <Tooltip formatter={(value) => `${(Number(value) * 100).toFixed(1)}%`} />
          <Legend />
          {orderedClasses.map((name) => (
            <Bar key={name} dataKey={name} name={name} fill={CLASS_COLORS[name]} radius={[4, 4, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function ConfusionMatrixHeatmap({ matrix }) {
  const order = ["retained", "weakened", "stopped"];
  const lookup = new Map(matrix.map((row) => [`${row.actual}|${row.predicted}`, row.users]));
  const max = Math.max(...matrix.map((row) => row.users), 1);

  return (
    <div>
      <div className="grid grid-cols-[90px_repeat(3,1fr)] gap-1 text-xs">
        <span />
        {order.map((state) => (
          <span key={state} className="pb-1 text-center font-black text-[#626D67]">
            예측 {CLASS_SHORT_LABELS[state]}
          </span>
        ))}
        {order.map((actual) => (
          <ConfusionRow key={actual} actual={actual} order={order} lookup={lookup} max={max} />
        ))}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-3 text-[11px] text-[#626D67]">
        <span className="flex items-center gap-1.5">
          <span
            className="h-3.5 w-3.5 rounded-sm"
            style={{ background: HEATMAP_STEPS[3], outline: "2px solid #17211D", outlineOffset: "-2px" }}
          />
          굵은 테두리 = 실제·예측 일치(대각선)
        </span>
        <span>색 진하기 = 인원수(n), 정확도가 아닙니다</span>
      </div>
      <div className="mt-2 flex items-center gap-2 text-[11px] text-[#626D67]">
        <span>낮음</span>
        <span
          className="h-2.5 w-32 rounded-full"
          style={{ background: `linear-gradient(to right, ${HEATMAP_STEPS.join(", ")})` }}
        />
        <span>높음</span>
      </div>
    </div>
  );
}

function ConfusionRow({ actual, order, lookup, max }) {
  return (
    <>
      <span className="flex items-center font-black text-[#626D67]">실제 {CLASS_SHORT_LABELS[actual]}</span>
      {order.map((predicted) => {
        const users = lookup.get(`${actual}|${predicted}`) ?? 0;
        const isDiagonal = actual === predicted;
        return (
          <div
            key={predicted}
            className="flex flex-col items-center justify-center gap-0.5 rounded-sm py-3 text-[#17211D]"
            style={{
              background: heatmapColor(users, max),
              outline: isDiagonal ? "2px solid #17211D" : undefined,
              outlineOffset: isDiagonal ? "-2px" : undefined,
            }}
          >
            <b className="text-sm">{users.toLocaleString()}</b>
            <span className="text-[10px] text-[#626D67]">명</span>
          </div>
        );
      })}
    </>
  );
}

function FeatureImportanceChart({ features }) {
  const top = [...features].sort((a, b) => a.rank - b.rank).slice(0, 10).reverse();
  const groups = [...new Set(top.map((item) => item.group))];

  return (
    <div>
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={top} layout="vertical" margin={{ top: 5, right: 30, bottom: 5, left: 10 }}>
            <CartesianGrid stroke="#E6EBE7" strokeDasharray="4 4" horizontal={false} />
            <XAxis type="number" axisLine={false} tickLine={false} tick={{ fill: "#626D67", fontSize: 11 }} />
            <YAxis type="category" dataKey="feature" width={190} axisLine={false} tickLine={false} tick={{ fill: "#17211D", fontSize: 10 }} />
            <Tooltip formatter={(value, _name, props) => [Number(value).toFixed(4), props.payload.group]} />
            <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
              {top.map((item) => (
                <Cell key={item.feature} fill={GROUP_COLORS[item.group] ?? "#9AA69F"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-[#626D67]">
        {groups.map((group) => (
          <span key={group} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: GROUP_COLORS[group] ?? "#9AA69F" }} />
            {group}
          </span>
        ))}
      </div>
    </div>
  );
}

const TREND_METRICS = [
  { key: "macroF1", label: "Macro F1" },
  { key: "macroPrAuc", label: "Macro PR-AUC" },
  { key: "macroRocAuc", label: "Macro ROC-AUC" },
  { key: "balancedAccuracy", label: "Balanced Accuracy" },
];

function VersionTrend({ before, after, beforeLabel, afterLabel, beforeSnapshot, afterSnapshot }) {
  return (
    <div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {TREND_METRICS.map(({ key, label }) => {
        const beforeValue = before?.[key];
        const afterValue = after?.[key];
        if (beforeValue === undefined || afterValue === undefined) return null;
        const delta = afterValue - beforeValue;
        const data = [
          { version: beforeLabel, value: beforeValue },
          { version: afterLabel, value: afterValue },
        ];
        return (
          <div key={key} className="rounded-lg border border-[#DDE4DF] p-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-black">{label}</p>
              <span className="text-[11px] font-black" style={{ color: delta >= 0 ? "#0ca30c" : "#d03b3b" }}>
                {delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(3)}
              </span>
            </div>
            <div className="mt-2 h-16 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
                  <XAxis dataKey="version" axisLine={false} tickLine={false} tick={{ fill: "#626D67", fontSize: 10 }} />
                  <YAxis hide domain={["dataMin - 0.02", "dataMax + 0.02"]} />
                  <Tooltip formatter={(value) => Number(value).toFixed(3)} />
                  <Line type="monotone" dataKey="value" stroke="#2a78d6" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        );
      })}
      </div>
      {beforeSnapshot && afterSnapshot && (
        <p className="mt-3 text-xs leading-5 text-[#626D67]">
          {beforeSnapshot.validationSamples === afterSnapshot.validationSamples &&
          beforeSnapshot.selectionYear === afterSnapshot.selectionYear &&
          beforeSnapshot.validationYear === afterSnapshot.validationYear ? (
            <>
              {beforeLabel}·{afterLabel} 모두 같은 검증 표본 {number(afterSnapshot.validationSamples)}명
              ({afterSnapshot.selectionYear}→{afterSnapshot.validationYear})으로 비교했습니다.
            </>
          ) : (
            <>
              {beforeLabel} 검증 표본 {number(beforeSnapshot.validationSamples)}명
              ({beforeSnapshot.selectionYear}→{beforeSnapshot.validationYear}),{" "}
              {afterLabel} 검증 표본 {number(afterSnapshot.validationSamples)}명
              ({afterSnapshot.selectionYear}→{afterSnapshot.validationYear})으로
              코호트와 검증 연도가 다릅니다.
            </>
          )}
        </p>
      )}
    </div>
  );
}

function ImportanceRow({ item, data }) {
  const maximum = Math.max(...data.map((entry) => entry.importance), 0.000001);
  return (
    <div className="rounded-lg bg-[#F6F8F6] p-3">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-black">{item.group}</p>
        <p className="text-xs font-black text-[#087A5A]">{item.featureCount}개</p>
      </div>
      <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-[#DCE5DF]"><span className="block h-full min-w-1 rounded-full bg-[#087A5A]" style={{ width: `${Math.max(4, (item.importance / maximum) * 100)}%` }} /></div>
    </div>
  );
}

// Track segments are sized by flex-grow proportional to the actual year gap
// (Math.max(1, ...) guards div-by-zero / same-year edge cases) so the line
// itself shows e.g. v02's 2-year selection→validation gap as visibly longer
// than its 1-year comparison→selection gap, instead of 3 evenly spaced boxes.
function DataLineageTimeline({ comparisonYear, selectionYear, validationYear }) {
  const gap1 = Math.max(1, (selectionYear ?? 0) - (comparisonYear ?? 0));
  const gap2 = Math.max(1, (validationYear ?? 0) - (selectionYear ?? 0));

  return (
    <div className="flex flex-col gap-3 md:flex-row md:items-start md:gap-0">
      <TimelineNode year={comparisonYear} title="비교 기준" description="이전 활동과 변화량 구성" />
      <TimelineConnector grow={gap1} years={gap1} />
      <TimelineNode year={selectionYear} title="선정·관찰" description="피처 마감과 운영 대상 선정" active />
      <TimelineConnector grow={gap2} years={gap2} />
      <TimelineNode year={validationYear} title="사후 검증" description="실제 상태 라벨로만 평가" />
    </div>
  );
}

function TimelineNode({ year, title, description, active = false }) {
  return (
    <div className="flex w-full shrink-0 flex-col items-center text-center md:w-40">
      <span
        className={`h-4 w-4 rounded-full border-2 ${active ? "border-[#087A5A] bg-[#087A5A]" : "border-[#9EAAA3] bg-white"}`}
      />
      <p className={`mt-2 text-xl font-black ${active ? "text-[#087A5A]" : ""}`}>{year ?? "-"}</p>
      <p className="mt-1 text-sm font-black">{title}</p>
      <p className="mt-1 text-xs text-[#626D67]">{description}</p>
    </div>
  );
}

function TimelineConnector({ grow, years }) {
  return (
    <div className="hidden flex-col items-center pt-[7px] md:flex" style={{ flexGrow: grow, flexBasis: 0 }}>
      <div className="relative h-0.5 w-full bg-[#DCE5DF]">
        <span className="absolute -right-px -top-[3px] h-0 w-0 border-y-4 border-l-4 border-y-transparent border-l-[#DCE5DF]" />
      </div>
      <span className="mt-1 text-[10px] text-[#9EAAA3]">{years}년</span>
    </div>
  );
}

function StatusBadge({ status }) {
  const tone = status === "operational"
    ? "bg-[#DFF1E8] text-[#087A5A]"
    : status === "candidate"
      ? "bg-[#E7F0FC] text-[#225EA8]"
      : "bg-[#EEF0EE] text-[#626D67]";
  return <span className={`rounded-full px-2 py-1 text-[10px] font-black ${tone}`}>{STATUS_LABELS[status] ?? status}</span>;
}

function ReferenceCard({ title, children }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-4">
      <p className="text-sm font-black">{title}</p>
      <p className="mt-2 text-xs leading-5 text-[#626D67]">{children}</p>
    </div>
  );
}

function EmptyState({ text }) {
  return <p className="rounded-lg bg-[#F6F8F6] p-5 text-sm text-[#626D67]">{text}</p>;
}

export default TrustCenterPage;
