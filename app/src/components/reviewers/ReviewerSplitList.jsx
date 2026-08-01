import StatusBadge from "./StatusBadge";

// Three signal bars from fields that actually exist on the worklist row —
// reviewCountDeclineRate and activeMonthDeclineRate are already 0–1 rates;
// recentRecencyDays is normalized against 200 days as a practical ceiling
// (p95 of the cohort is well under that). No fourth bar: the summary row
// doesn't carry a real explore-range field, and making one up isn't worth a
// prettier grid.
function SignalStrip({ reviewer }) {
  const bars = [
    Math.min(1, reviewer.reviewCountDeclineRate ?? 0),
    Math.min(1, reviewer.activeMonthDeclineRate ?? 0),
    Math.min(1, (reviewer.recentRecencyDays ?? 0) / 200),
  ];

  return (
    <span className="flex h-3.5 items-end gap-[3px]" title="리뷰 감소율 · 활동월 감소율 · 최근 공백일">
      {bars.map((value, index) => (
        <span
          key={index}
          className="w-1 rounded-[1px]"
          style={{
            height: `${Math.max(15, value * 100)}%`,
            background: value >= 0.6 ? "#E15D47" : value >= 0.3 ? "#A66A18" : "#B7CFC2",
          }}
        />
      ))}
    </span>
  );
}

function ReviewerSplitList({
  reviewers,
  activeReviewerId,
  onSelect,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
}) {
  const allSelected =
    reviewers.length > 0 && reviewers.every((r) => selectedIds.has(r.userId));

  return (
    <div className="overflow-hidden rounded-lg border border-[#DDE4DF] bg-white">
      <div className="grid grid-cols-[24px_84px_1fr_100px_56px] items-center gap-2.5 border-b border-[#DDE4DF] px-2 py-1.5 text-[11px] text-[#626D67]">
        <label className="flex h-6 w-6 items-center justify-center">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={() => onToggleSelectAll(reviewers.map((r) => r.userId))}
            className="h-3.5 w-3.5"
            aria-label="전체 선택"
          />
        </label>
        <span title="통합 우선순위 기준 순위입니다 — 중단·약화 점수를 합친 상대 검토 순위이며 보정된 이탈 확률이 아닙니다.">
          우선순위
        </span>
        <span>리뷰어 · 위험 유형</span>
        <span title="리뷰 감소율 · 활동월 감소율 · 최근 공백일">신호</span>
        <span className="text-center">판단</span>
      </div>

      {reviewers.map((reviewer) => {
        const isActive = reviewer.userId === activeReviewerId;
        const isSelected = selectedIds.has(reviewer.userId);
        const isCompleted = Boolean(reviewer.managerDecision);

        return (
          <div
            key={reviewer.userId}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(reviewer)}
            onKeyDown={(event) => {
              if (event.key === "Enter") onSelect(reviewer);
            }}
            className={[
              "grid min-h-8 cursor-pointer grid-cols-[24px_84px_1fr_100px_56px] items-center gap-2.5 border-b border-[#F1F4F1] px-2 text-xs outline-none transition last:border-b-0 focus-visible:ring-2 focus-visible:ring-[#137A5A]",
              isActive
                ? "border-l-2 border-l-[#137A5A] bg-white pl-[6px]"
                : isSelected
                  ? "bg-[#E3F1EA]"
                  : "hover:bg-[#F6F8F6]",
              isCompleted ? "opacity-60" : "",
            ].join(" ")}
          >
            <label
              className="flex h-full w-full items-center justify-center"
              onClick={(event) => event.stopPropagation()}
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => onToggleSelect(reviewer.userId)}
                className="h-3.5 w-3.5"
                aria-label={`${reviewer.userId} 선택`}
              />
            </label>

            <span className="text-[#626D67]">{reviewer.priorityRank}위</span>

            <span className="min-w-0">
              <span
                className={`block truncate ${isCompleted ? "line-through" : "font-medium"}`}
              >
                {reviewer.userId}
              </span>
              <span className="block truncate text-[11px] text-[#626D67]">
                {isCompleted ? reviewer.managerDecision : reviewer.riskType}
              </span>
            </span>

            <SignalStrip reviewer={reviewer} />

            <span className="flex justify-center">
              {isCompleted ? (
                <span className="text-[#137A5A]">✓</span>
              ) : (
                <StatusBadge judgment={reviewer.modelJudgment} />
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default ReviewerSplitList;
