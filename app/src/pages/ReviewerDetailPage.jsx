import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import ActivitySummaryChart from "../components/reviewer-detail/ActivitySummaryChart";
import ReviewIntervalChart from "../components/reviewer-detail/ReviewIntervalChart";
import ActivityChangeGrid from "../components/reviewer-detail/ActivityChangeGrid";
import DecisionPanel from "../components/reviewer-detail/DecisionPanel";
import EvidenceList from "../components/reviewer-detail/EvidenceList";
import MonthlyActivityChart from "../components/reviewer-detail/MonthlyActivityChart";
import ReviewerScoreBars from "../components/reviewer-detail/ReviewerScoreBars";
import StatusBadge from "../components/reviewers/StatusBadge";
import { useOperationsSummary, useReviewers } from "../context/operations-context";
import {
  formatTopPercent,
  loadReviewerDetails,
  strategyFor,
} from "../data";
import {
  getDecision,
  removeDecision,
  saveDecision,
} from "../services/decisionStorage";

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
  const operationsSummary = useOperationsSummary();
  const reviewers = useReviewers();
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
  const [savedDecision, setSavedDecision] = useState(() =>
    reviewer
      ? getDecision(operationsSummary.modelVersion, reviewer.sampleId)
      : null,
  );

  // Detail lives in a separate file that is fetched once and reused for every
  // reviewer opened afterwards.
  const [details, setDetails] = useState(null);
  const [detailError, setDetailError] = useState(null);

  useEffect(() => {
    let active = true;

    loadReviewerDetails()
      .then((loaded) => {
        if (active) {
          setDetails(loaded);
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
  }, []);

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

  const loadedDetail = details?.[reviewer.userId] ?? null;

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
    strategy: strategyFor(loadedDetail?.predictedState ?? 0, reviewer.riskType),
  };

  const recommendedDecision = reviewer.recommendedDecision;

  function handleSaveDecision(decision) {
    saveDecision(operationsSummary.modelVersion, reviewer.sampleId, decision);
    setSavedDecision(decision);
  }

  function handleCancelDecision() {
    removeDecision(operationsSummary.modelVersion, reviewer.sampleId);
    setSavedDecision(null);
  }

  return (
    <section>
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <Link
          to="/reviewers"
          className="font-bold text-[#137A5A]"
        >
          ← 리뷰어 관리
        </Link>

        <label className="flex items-center gap-2 text-sm text-[#68736D]">
          <input
            type="checkbox"
            checked={validationMode}
            onChange={(event) =>
              setValidationMode(event.target.checked)
            }
            className="h-4 w-4 accent-[#137A5A]"
          />

          검증 정답 표시
        </label>
      </div>

      <div className="mt-5 grid grid-cols-[1fr_auto_1fr] items-center rounded-xl border border-[#DDE4DF] bg-white px-5 py-3">
        <div>
          {previousReviewer ? (
            <Link
              to={`/reviewers/${previousReviewer.userId}`}
              className="font-bold text-[#137A5A]"
            >
              ← 이전 리뷰어
            </Link>
          ) : (
            <span className="text-[#B3BBB6]">
              ← 이전 리뷰어
            </span>
          )}
        </div>

        <p className="text-center text-sm text-[#68736D]">
          워크리스트 순서 기준 · {currentIndex + 1} /{" "}
          {orderedReviewers.length}
        </p>

        <div className="text-right">
          {nextReviewer ? (
            <Link
              to={`/reviewers/${nextReviewer.userId}`}
              className="font-bold text-[#137A5A]"
            >
              다음 리뷰어 →
            </Link>
          ) : (
            <span className="text-[#B3BBB6]">
              다음 리뷰어 →
            </span>
          )}
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-[#DDE4DF] bg-white p-6">
        <div className="flex flex-col justify-between gap-5 md:flex-row">
          <div>
            <h1 className="text-2xl font-bold text-[#17211D]">
              {detail.userId}
            </h1>

            <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-full bg-[#F1F4F1] px-3 py-1 text-xs text-[#68736D]">
                전체 {detail.totalReviewers.toLocaleString()}명 중{" "}
                {detail.priorityRank}위 · 상위{" "}
                {formatTopPercent(detail.priorityTopPercent)}
              </span>

              <StatusBadge
                judgment={detail.modelJudgment}
              />

              <span className="rounded-full bg-[#F1F4F1] px-3 py-1 text-xs text-[#68736D]">
                {detail.riskType}
              </span>

              <span className="rounded-full bg-[#F1F4F1] px-3 py-1 text-xs text-[#68736D]">
                {detail.crmTargetLabel}
              </span>
            </div>
          </div>

          <div className="text-sm text-[#68736D] md:text-right">
            <p>
              비교 {detail.comparisonYear} · 선정{" "}
              {detail.selectionYear} · 검증 {detail.targetYear}
            </p>

            <p className="mt-2 text-xs">
              {operationsSummary.dataModeLabel} Reviewer 360
            </p>
          </div>
        </div>

        <ReviewerScoreBars scores={detail.scores} />
      </div>

      <div className="mt-8">
        <div className="mb-4">
          <h2 className="text-2xl font-bold text-[#17211D]">
            활동이 이렇게 변했습니다
          </h2>

          <p className="mt-2 text-sm text-[#68736D]">
            선정 기간과 최근 관찰 기간을 같은 기준으로
            비교했습니다.
          </p>
        </div>

        {detailError ? (
          <p className="rounded-xl bg-[#F7E8E5] px-5 py-4 text-sm text-[#E15D47]">
            {detailError}
          </p>
        ) : loadedDetail ? (
          <ActivityChangeGrid changes={detail.changes} />
        ) : (
          <p className="rounded-xl bg-[#F1F4F1] px-5 py-4 text-sm text-[#68736D]">
            활동 상세를 불러오는 중입니다.
          </p>
        )}
      </div>

      <div className="mt-8 grid gap-7 xl:grid-cols-[1.7fr_0.8fr]">
        <div>
          <h2 className="text-xl font-bold text-[#17211D]">
            왜 우선 검토 대상인가
          </h2>

          <p className="mt-2 text-sm text-[#68736D]">
            관찰 가능한 근거를 강한 순서로 정리했습니다.
          </p>

          <div className="mt-4">
            <EvidenceList evidence={detail.evidence} />
          </div>

          <div className="mt-8 rounded-xl border border-[#DDE4DF] bg-white p-5">
            <p className="text-xs font-bold tracking-widest text-[#4C987C]">
              RECOMMENDED PLAYBOOK
            </p>

            <h2 className="mt-3 text-xl font-bold text-[#17211D]">
              {detail.strategy.title}
            </h2>

            <p className="mt-3 text-sm leading-6 text-[#68736D]">
              {detail.strategy.description}
            </p>

            <div className="mt-5 space-y-3 border-t border-[#DDE4DF] pt-4 text-sm">
              <StrategyRow
                label="핵심 신호"
                value={detail.riskType}
              />

              <StrategyRow
                label="전략 후보"
                value={detail.strategy.secondary}
              />

              <StrategyRow
                label="향후 채널"
                value={detail.strategy.channel}
              />
            </div>

            <Link
              to={`/playbook?reviewer=${encodeURIComponent(detail.userId)}`}
              className="mt-5 flex min-h-11 items-center justify-center rounded-lg border border-[#137A5A] font-bold text-[#137A5A] hover:bg-[#E3F1EA]"
            >
              플레이북에서 전략 확인
            </Link>
          </div>
        </div>

        <DecisionPanel
          savedDecision={savedDecision}
          recommendedDecision={recommendedDecision}
          onSave={handleSaveDecision}
          onCancel={handleCancelDecision}
          previousReviewer={previousReviewer}
          nextReviewer={nextReviewer}
        />
      </div>

      <div className="mt-10">
        <div className="flex overflow-x-auto border-b border-[#DDE4DF]">
          {detailTabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setDetailView(tab.key)}
              className={[
                "min-w-32 border-b-2 px-5 py-3 text-sm font-bold transition",
                detailView === tab.key
                  ? "border-[#137A5A] text-[#137A5A]"
                  : "border-transparent text-[#68736D]",
              ].join(" ")}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="mt-5">
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
              <p className="rounded-xl bg-[#F7E8E5] px-5 py-4 text-sm text-[#E15D47]">
                {detailError}
              </p>
            ) : loadedDetail ? (
              <MonthlyActivityChart
                data={detail.monthlyActivity}
                comparisonYear={detail.comparisonYear}
                selectionYear={detail.selectionYear}
              />
            ) : (
              <p className="rounded-xl bg-[#F1F4F1] px-5 py-4 text-sm text-[#68736D]">
                월별 활동 데이터를 불러오는 중입니다.
              </p>
            ))}

          {detailView === "validation" &&
            !validationMode && (
              <div className="rounded-xl bg-[#F1F4F1] p-7">
                <h3 className="font-bold text-[#17211D]">
                  사후 검증 결과가 숨겨져 있습니다
                </h3>

                <p className="mt-2 text-sm text-[#68736D]">
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
      </div>

      <footer className="mt-12 border-t border-[#DDE4DF] pt-5 text-xs text-[#68736D]">
        Reviewer Retention · {operationsSummary.dataModeLabel} data · 클래스
        점수는 보정 확률이 아니며 통합 점수는 운영 우선순위에 사용합니다.
      </footer>
    </section>
  );
}

function StrategyRow({ label, value }) {
  return (
    <div className="flex justify-between gap-5 border-b border-[#DDE4DF] pb-3 last:border-b-0">
      <span className="text-[#68736D]">
        {label}
      </span>

      <strong className="max-w-[65%] text-right font-semibold text-[#17211D]">
        {value}
      </strong>
    </div>
  );
}

function ValidationCard({ label, value }) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-5">
      <p className="text-sm text-[#68736D]">
        {label}
      </p>

      <p className="mt-3 text-xl font-bold text-[#17211D]">
        {value}
      </p>
    </div>
  );
}

export default ReviewerDetailPage;
