import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router";
import ActivitySummaryChart from "../components/reviewer-detail/ActivitySummaryChart";
import ActivityStoryStage from "../components/reviewer-detail/ActivityStoryStage";
import ReviewActivityRadius from "../components/reviewer-detail/ReviewActivityRadius";
import ReviewIntervalChart from "../components/reviewer-detail/ReviewIntervalChart";
import DecisionPanel from "../components/reviewer-detail/DecisionPanel";
import ErrorState from "../components/common/ErrorState";
import Skeleton from "../components/common/Skeleton";
import EvidenceList from "../components/reviewer-detail/EvidenceList";
import MonthlyActivityChart from "../components/reviewer-detail/MonthlyActivityChart";
import GlobalWorkflowStepper from "../components/workflow/GlobalWorkflowStepper";
import { useOperationsSummary, useReviewers } from "../context/operations-context";
import { useDecisions } from "../context/DecisionContext";
import {
  getCachedReviewerDetail,
  loadReviewerDetail,
  loadReviewerRecommendations,
} from "../data";

// Links EvidenceList's `group` field (shared/retention/insights.py's
// classify_risk_type: 활동량 / 작성 간격 / 탐색 활동) to the change rows
// it's actually derived from, so hovering an evidence item highlights the
// specific metrics behind it instead of a guessed text match (B-5).
const GROUP_TO_CHANGE_LABELS = {
  활동량: ["리뷰 수", "활동 월"],
  "작성 간격": ["리뷰 공백"],
  "탐색 활동": ["고유 음식점"],
};

const detailTabs = [
  {
    key: "activity",
    label: "활동 변화",
  },
  {
    key: "interval",
    label: "작성 주기",
  },
  {
    key: "timeline",
    label: "월별 타임라인",
  },
  {
    key: "validation",
    label: "사후 검증",
  },
];

// Keyed by reviewerId so moving between reviewers remounts the screen. That
// resets the open tab, the disclosure toggle and the loaded decision without
// an effect that would have to chase every prop change.
function ReviewerDetailPage() {
  const { reviewerId } = useParams();

  return <ReviewerDetail key={reviewerId} reviewerId={reviewerId} />;
}

function ReviewerDetail({ reviewerId }) {
  const location = useLocation();
  const operationsSummary = useOperationsSummary();
  const reviewers = useReviewers();
  const { decisions, saveForReviewer, removeForReviewer } = useDecisions();
  const orderedReviewers = [...reviewers].sort(
    (first, second) =>
      first.priorityRank - second.priorityRank,
  );

  const currentIndex = orderedReviewers.findIndex(
    (reviewer) => reviewer.userId === reviewerId,
  );

  const reviewer =
    currentIndex >= 0
      ? orderedReviewers[currentIndex]
      : null;

  const previousReviewer =
    currentIndex > 0
      ? orderedReviewers[currentIndex - 1]
      : null;

  const nextReviewer =
    currentIndex >= 0 &&
    currentIndex < orderedReviewers.length - 1
      ? orderedReviewers[currentIndex + 1]
      : null;

  const [detailView, setDetailView] = useState("activity");
  const [validationMode, setValidationMode] = useState(false);
  const [hoveredGroup, setHoveredGroup] = useState(null);
  const savedRecord = reviewer ? decisions[reviewer.userId] ?? null : null;

  useEffect(() => {
    if (window.location.hash !== "#manager-decision") return undefined;
    const frame = window.requestAnimationFrame(() => {
      const target = document.getElementById("manager-decision");
      if (!target) return;
      target.focus({ preventScroll: true });
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [reviewerId]);

  // Detail is fetched per reviewer and cached by userId. This page remounts
  // on every reviewerId change (see the wrapper below), so starting from the
  // module-level cache instead of null avoids re-showing a loading state on
  // a reviewer that was already opened this session (B-11).
  const [loadedDetail, setLoadedDetail] = useState(() =>
    getCachedReviewerDetail(reviewerId),
  );
  const [detailError, setDetailError] = useState(null);
  const [recommendationData, setRecommendationData] = useState(null);

  useEffect(() => {
    let active = true;

    loadReviewerDetail(reviewerId)
      .then((loaded) => {
        if (active) {
          setLoadedDetail(loaded);
        }
      })
      .catch((error) => {
        if (active) {
          setDetailError(error.message);
        }
      });

    return () => {
      active = false;
    };
  }, [reviewerId]);

  useEffect(() => {
    let active = true;
    loadReviewerRecommendations(reviewerId)
      .then((data) => {
        if (active && data.available) setRecommendationData(data);
      })
      .catch(() => {
        // Recommendations are supplementary and must not block Reviewer 360.
      });
    return () => {
      active = false;
    };
  }, [reviewerId]);

  if (!reviewer) {
    return (
      <section>
        <h1 className="text-3xl font-bold text-[#17211D]">
          리뷰어를 찾을 수 없습니다
        </h1>

        <Link
          to="/reviewers"
          className="mt-5 inline-flex font-bold text-[#137A5A]"
        >
          ← 리뷰어 관리로 돌아가기
        </Link>
      </section>
    );
  }

  const detail = {
    // Empty collections keep the charts and lists renderable during the fetch.
    activitySummary: [],
    intervalComparison: [],
    changes: [],
    evidence: [],
    monthlyActivity: [],
    actual: { state: "—", targetReviewCount: 0, targetActiveMonths: 0 },
    ...reviewer,
    ...loadedDetail,
    totalReviewers: operationsSummary.totalReviewers,
  };

  const recommendedDecision = reviewer.recommendedDecision;

  function handleSaveDecision(changes) {
    return saveForReviewer(reviewer, changes);
  }

  function handleCancelDecision() {
    return removeForReviewer(reviewer.userId);
  }

  const queueHref = `/reviewers${location.search}`;
  const reviewerHref = (id) => `/reviewers/${id}${location.search}`;
  const workflowSteps = [
    { label: "운영 신호 확인", href: `/${location.search}` },
    { label: "대상 선정", href: queueHref },
    { label: "근거 검토·판단" },
    savedRecord
      ? { label: "운영안 설계", href: `/playbook?mode=individual&reviewer=${encodeURIComponent(detail.userId)}` }
      : { label: "운영안 설계" },
    { label: "실행·성과 추적" },
  ];

  return (
    <section className="pb-4">
      <GlobalWorkflowStepper steps={workflowSteps} currentStep={3} />

      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2 rounded-xl border border-[#DDE4DF] bg-white px-4 py-3 shadow-[0_4px_14px_rgba(23,33,29,0.04)]">
        <div className="flex min-w-[260px] items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-full bg-[#E3F1EA] text-lg text-[#075C45]">●</span>
          <div><p className="text-[9px] font-black tracking-[0.14em] text-[#137A5A]">SELECTED REVIEWER</p><p className="text-sm font-black text-[#17211D]">{detail.userId}</p></div>
        </div>
        <SummaryMetric label="공급 위험 우선순위" value={`${detail.priorityRank}위 / ${detail.totalReviewers.toLocaleString()}명`} />
        <SummaryMetric label="모델 판단(등급)" value={detail.modelJudgment} badge />
        <SummaryMetric label="위험 유형" value={detail.riskType} />
        <SummaryMetric label="관리자 판단" value={savedRecord?.decision ?? "미검토"} />
        <SummaryMetric label="관찰 기간" value={`${detail.comparisonYear} → ${detail.selectionYear}`} />
        <div className="ml-auto flex items-center gap-3 text-[11px] font-bold">
          {previousReviewer && <Link to={reviewerHref(previousReviewer.userId)} className="text-[#626D67] hover:text-[#075C45]">← 이전</Link>}
          <Link to={queueHref} className="text-[#075C45] underline underline-offset-4">검토 큐</Link>
          {nextReviewer && <Link to={reviewerHref(nextReviewer.userId)} className="text-[#075C45]">다음 →</Link>}
        </div>
      </div>

      <div className="mt-3 grid items-stretch gap-3 xl:grid-cols-[minmax(0,1.62fr)_390px]">
        <div className="flex min-w-0 flex-col gap-4">
          {detailError ? <ErrorState message={detailError} /> : loadedDetail ? <ActivityStoryStage changes={detail.changes} comparisonYear={detail.comparisonYear} selectionYear={detail.selectionYear} highlightedLabels={GROUP_TO_CHANGE_LABELS[hoveredGroup] ?? []} priorActivityAvailable={detail.priorActivityAvailable} evidence={detail.evidence} /> : <Skeleton rows={4} columns={3} />}

          <ReviewActivityRadius userId={detail.userId} recommendationData={recommendationData} />

        </div>

        <aside id="manager-decision" tabIndex={-1} className="flex h-full min-w-0 flex-col gap-3 scroll-mt-20 rounded-xl transition focus:outline-none target:ring-2 target:ring-[#46A986] target:ring-offset-4">
          <DecisionPanel
            reviewer={reviewer}
            modelVersion={operationsSummary.modelVersion}
            savedRecord={savedRecord}
            recommendedDecision={recommendedDecision}
            interventionHref={`/playbook?mode=individual&reviewer=${encodeURIComponent(detail.userId)}`}
            onSave={handleSaveDecision}
            onCancel={handleCancelDecision}
          />
          <section className="flex min-h-0 flex-1 flex-col rounded-xl border border-[#DDE4DF] bg-white p-3">
            <div className="mb-2 flex items-center justify-between gap-3">
              <div><p className="text-[9px] font-black tracking-[0.12em] text-[#137A5A]">DECISION EVIDENCE</p><h2 className="mt-0.5 text-sm font-black text-[#17211D]">판단 근거</h2></div>
              <p className="text-[9px] text-[#718078]">근거 hover 시 지표 강조</p>
            </div>
            <EvidenceList evidence={detail.evidence} hoveredGroup={hoveredGroup} onHoverGroup={setHoveredGroup} compact />
          </section>
        </aside>
      </div>

      <details className="mt-4 overflow-hidden rounded-xl border border-[#DDE4DF] bg-white">
        <summary className="cursor-pointer px-4 py-3 text-xs font-black text-[#17211D]">보조 분석 · 활동 변화 / 작성 주기 / 월별 타임라인 / 사후 검증</summary>
      <section className="border-t border-[#DDE4DF]">
        <div className="flex items-center justify-between gap-4 border-b border-[#DDE4DF] px-4">
          <p className="hidden text-xs font-black text-[#17211D] lg:block">보조 분석</p>
          <div className="flex overflow-x-auto">
          {detailTabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setDetailView(tab.key)}
              className={[
                "min-w-28 border-b-2 px-4 py-3 text-xs font-bold transition",
                detailView === tab.key
                  ? "border-[#137A5A] text-[#137A5A]"
                  : "border-transparent text-[#626D67]",
              ].join(" ")}
            >
              {tab.label}
            </button>
          ))}
          </div>
          <label className="flex shrink-0 items-center gap-1.5 text-[10px] font-bold text-[#626D67]"><input type="checkbox" checked={validationMode} onChange={(event) => setValidationMode(event.target.checked)} className="h-3.5 w-3.5 accent-[#075C45]" />사후 검증 표시</label>
        </div>

        <div className="p-4">
          {detailView === "activity" && (
            <ActivitySummaryChart
              data={detail.activitySummary}
            />
          )}

          {detailView === "interval" && (
            <ReviewIntervalChart
              data={detail.intervalComparison}
            />
          )}

          {detailView === "timeline" &&
            (detailError ? (
              <p className="rounded-xl bg-[#F7E8E5] px-5 py-4 text-sm text-[#BF3620]">
                {detailError}
              </p>
            ) : loadedDetail ? (
              <MonthlyActivityChart
                data={detail.monthlyActivity}
                comparisonYear={detail.comparisonYear}
                selectionYear={detail.selectionYear}
              />
            ) : (
              <p className="rounded-xl bg-[#F1F4F1] px-5 py-4 text-sm text-[#626D67]">
                월별 활동 데이터를 불러오는 중입니다.
              </p>
            ))}

          {detailView === "validation" &&
            !validationMode && (
              <div className="rounded-xl bg-[#F1F4F1] p-7">
                <h3 className="font-bold text-[#17211D]">
                  사후 검증 결과가 숨겨져 있습니다
                </h3>

                <p className="mt-2 text-sm text-[#626D67]">
                  화면 상단의 검증 정답 표시를 켜야 실제 결과를
                  확인할 수 있습니다.
                </p>
              </div>
            )}

          {detailView === "validation" &&
            validationMode && (
              <div>
                <div className="mb-4 rounded-lg bg-[#E6EFF1] px-4 py-3 text-sm text-[#356A78]">
                  운영 당시에는 알 수 없었던 사후 결과입니다.
                  예측 근거와 분리해 표시합니다.
                </div>

                <div className="grid gap-4 md:grid-cols-3">
                  <ValidationCard
                    label="실제 상태"
                    value={detail.actual.state}
                  />

                  <ValidationCard
                    label="타깃 연도 리뷰"
                    value={`${detail.actual.targetReviewCount}건`}
                  />

                  <ValidationCard
                    label="타깃 연도 활동 월"
                    value={`${detail.actual.targetActiveMonths}개월`}
                  />
                </div>
              </div>
            )}
        </div>
      </section>
      </details>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs text-[#626D67]">
        Reviewer Retention · {operationsSummary.dataModeLabel} data · 클래스
        점수는 보정 확률이 아니며 통합 점수는 운영 우선순위에 사용합니다.
      </footer>
    </section>
  );
}

function SummaryMetric({ label, value, badge = false }) {
  return (
    <div className="min-w-[115px] border-l border-[#E1E6E3] pl-4">
      <p className="text-[9px] text-[#718078]">{label}</p>
      <p className={`mt-1 text-xs font-black ${badge ? "text-[#BF3620]" : "text-[#17211D]"}`}>{value}</p>
    </div>
  );
}

function ValidationCard({ label, value }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <p className="text-sm text-[#626D67]">
        {label}
      </p>

      <p className="mt-3 text-xl font-bold text-[#17211D]">
        {value}
      </p>
    </div>
  );
}

export default ReviewerDetailPage;
