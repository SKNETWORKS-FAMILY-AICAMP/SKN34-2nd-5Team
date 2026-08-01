import { useEffect, useState } from "react";
import { Link } from "react-router";

import { getCachedReviewerDetail, loadReviewerDetail, strategyFor } from "../../data";
import { useDecisions } from "../../context/DecisionContext";

const decisionOptions = [
  "리뷰 다시 시작 유도",
  "리뷰 활동 늘리기",
  "변화 지켜보기",
  "이번엔 제외",
];

// Split-view companion to DecisionPanel — same save semantics, but "next"
// means "advance selection within this list" instead of navigating to a
// different full page, and there's no prev/next full-page nav here.
function ReviewerSplitPanel({ reviewer, onAdvance }) {
  const { decisions, saveForReviewer, removeForReviewer } = useDecisions();
  const [detail, setDetail] = useState(() =>
    getCachedReviewerDetail(reviewer.userId),
  );
  const evidence = detail ? (detail.evidence ?? []) : null;
  // strategyFor falls back to a neutral default when predictedState is
  // still unknown (evidence not loaded yet) — safe to call unconditionally.
  const strategy = strategyFor(detail?.predictedState, reviewer.riskType);
  const [selectedDecision, setSelectedDecision] = useState("");
  const savedDecision = decisions[reviewer.userId]?.decision ?? null;
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);

  // Parent keys this component by reviewer.userId, so a reviewer change
  // remounts it and the useState initializers above already give a clean
  // slate — this effect only needs to fetch evidence, not reset state.
  useEffect(() => {
    let active = true;
    loadReviewerDetail(reviewer.userId)
      .then((loaded) => {
        if (active) setDetail(loaded ?? {});
      })
      .catch(() => {
        if (active) setDetail({});
      });
    return () => {
      active = false;
    };
  }, [reviewer.userId]);

  async function persist(decision) {
    setSaving(true);
    setSaveError("");
    try {
      await saveForReviewer(reviewer, { decision });
      return true;
    } catch (error) {
      setSaveError(error.message);
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveOnly() {
    if (!selectedDecision) return;
    if (await persist(selectedDecision)) setConfirmVisible(false);
  }

  async function handleSaveAndAdvance() {
    if (!selectedDecision) return;
    if (await persist(selectedDecision)) setConfirmVisible(true);
  }

  async function handleUndo() {
    setSaving(true);
    setSaveError("");
    try {
      await removeForReviewer(reviewer.userId);
      setConfirmVisible(false);
    } catch (error) {
      setSaveError(error.message);
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    function onKeyDown(event) {
      const tag = document.activeElement?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      const index = Number(event.key) - 1;
      if (index >= 0 && index < decisionOptions.length) {
        setSelectedDecision(decisionOptions[index]);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="rounded-lg border border-[#DDE4DF] bg-white p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-[#17211D]">{reviewer.userId}</p>
        <Link
          to={`/reviewers/${encodeURIComponent(reviewer.userId)}`}
          className="shrink-0 text-[11px] font-medium text-[#137A5A] underline"
        >
          Reviewer 360 전체 보기
        </Link>
      </div>
      <p className="mt-0.5 text-[11px] text-[#626D67]">
        {reviewer.priorityRank}위 · 상위{" "}
        {reviewer.priorityTopPercent < 0.1
          ? "0.1% 이내"
          : `${reviewer.priorityTopPercent.toFixed(1)}%`}{" "}
        · {reviewer.riskType}
      </p>

      <p className="mt-2.5 rounded bg-[#F7F8F5] px-2.5 py-2 text-xs leading-5">
        {reviewer.coreChange}
      </p>

      <p className="mt-2.5 text-[11px] text-[#626D67]">근거</p>
      {evidence === null ? (
        <p className="text-xs text-[#B3BBB6]">불러오는 중…</p>
      ) : evidence.length === 0 ? (
        <p className="text-xs text-[#B3BBB6]">근거 데이터 없음</p>
      ) : (
        evidence.slice(0, 3).map((item, index) => (
          <p key={item.title} className="text-xs">
            {index + 1}. {item.evidence}
          </p>
        ))
      )}

      <p className="mt-2.5 border-t border-[#F1F4F1] pt-2 text-[11px] text-[#626D67]">
        관리자 판단
      </p>

      {decisionOptions.map((option, index) => (
        <label
          key={option}
          className={[
            "mb-1 flex min-h-8 cursor-pointer items-center gap-2 rounded border px-2 text-xs transition",
            selectedDecision === option
              ? "border-[#137A5A] bg-[#E3F1EA]"
              : "border-[#DDE4DF] hover:bg-[#F6F8F6]",
          ].join(" ")}
        >
          <input
            type="radio"
            name={`decision-${reviewer.userId}`}
            checked={selectedDecision === option}
            onChange={() => setSelectedDecision(option)}
            className="accent-[#137A5A]"
          />
          <span className="flex-1">{option}</span>
          <span
            className={[
              "rounded border px-1 text-[10px]",
              selectedDecision === option
                ? "border-[#137A5A] text-[#137A5A]"
                : "border-[#DDE4DF] text-[#626D67]",
            ].join(" ")}
          >
            {index + 1}
          </span>
        </label>
      ))}

      {savedDecision && !confirmVisible && (
        <div className="mt-1 flex items-center justify-between gap-2">
          <p className="text-[11px] text-[#137A5A]">
            판단 완료 · {savedDecision}
          </p>
          <button
            type="button"
            onClick={handleUndo}
            disabled={saving}
            className="text-[11px] font-medium text-[#626D67] hover:text-[#BF3620] disabled:cursor-not-allowed disabled:opacity-40"
          >
            취소
          </button>
        </div>
      )}

      <div className="mt-2 flex gap-1.5">
        <button
          type="button"
          onClick={handleSaveOnly}
          disabled={!selectedDecision || saving}
          className="flex-1 min-h-8 rounded border border-[#137A5A] text-[11px] font-medium text-[#137A5A] transition hover:bg-[#E3F1EA] disabled:cursor-not-allowed disabled:opacity-40"
        >
          판단만 저장
        </button>
        <button
          type="button"
          onClick={handleSaveAndAdvance}
          disabled={!selectedDecision || saving}
          className="flex-[1.4] min-h-8 rounded bg-[#137A5A] text-[11px] font-medium text-white transition hover:bg-[#185C46] disabled:cursor-not-allowed disabled:opacity-40"
        >
          저장하고 다음 미검토
        </button>
      </div>

      {confirmVisible && (
        <div className="mt-2 rounded bg-[#137A5A] p-2.5 text-xs text-white">
          <p className="font-medium">판단과 변경 이력이 서버에 저장되었습니다</p>

          <div className="mt-2 rounded bg-[#185C46] px-2.5 py-2">
            <p className="text-[10px] font-medium tracking-wide text-[#CFE7DC]">
              추천 플레이북
            </p>
            <p className="mt-0.5 font-medium">{strategy.title}</p>
            {strategy.description && (
              <p className="mt-1 text-[11px] leading-4 text-[#CFE7DC]">
                {strategy.description}
              </p>
            )}
          </div>

          <div className="mt-2 flex gap-3 text-[11px] text-[#CFE7DC]">
            <button type="button" onClick={handleUndo} className="underline">
              실행 취소
            </button>
            <Link
              to={`/playbook?reviewer=${encodeURIComponent(reviewer.userId)}`}
              className="underline"
            >
              전체 플레이북에서 보기
            </Link>
            <button
              type="button"
              onClick={() => onAdvance(reviewer.userId)}
              className="ml-auto underline"
            >
              다음 리뷰어 →
            </button>
          </div>
        </div>
      )}

      {saveError && (
        <p className="mt-2 text-[11px] text-[#BF3620]">{saveError}</p>
      )}
    </div>
  );
}

export default ReviewerSplitPanel;
