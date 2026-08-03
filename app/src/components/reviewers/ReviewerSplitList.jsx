import { DECISION_TONES } from "../../data/decisionTones";

const ROW_GRID = "grid-cols-[28px_minmax(165px,1.25fr)_70px_110px_minmax(155px,1fr)_90px_92px]";

function statusLabel(reviewer) {
  return reviewer.managerDecision ? "검토 완료" : "미검토";
}

function observationFor(reviewer, scope) {
  if (scope === "newcomers") return { icon: "star", label: "신규 코호트 진입", tone: "text-[#B28618]" };

  const riskType = String(reviewer.riskType ?? "");
  if (riskType.includes("활동량")) return { icon: "trend", label: "리뷰 활동 감소", tone: "text-[#E64A35]" };
  if (riskType.includes("작성 주기")) return { icon: "calendar", label: "작성 공백 증가", tone: "text-[#D97819]" };
  if (riskType.includes("탐색")) return { icon: "search", label: "탐색 활동 축소", tone: "text-[#3979B7]" };
  if ((reviewer.reviewCountDeclineRate ?? 0) > 0) return { icon: "trend", label: "리뷰 활동 감소", tone: "text-[#E64A35]" };
  if ((reviewer.activeMonthDeclineRate ?? 0) > 0) return { icon: "calendar", label: "활동 월 감소", tone: "text-[#E45F54]" };
  if ((reviewer.recentRecencyDays ?? 0) >= 150) return { icon: "calendar", label: "작성 공백 증가", tone: "text-[#D97819]" };
  return { icon: "signals", label: "복합 약화 신호", tone: "text-[#7A5BA7]" };
}

function SignalIcon({ name }) {
  const common = { width: 15, height: 15, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };
  if (name === "trend") return <svg {...common}><path d="m4 6 6 6 4-4 6 6" /><path d="M16 14h4v-4" /></svg>;
  if (name === "calendar") return <svg {...common}><rect x="4" y="5.5" width="16" height="14" rx="2" /><path d="M8 3v5M16 3v5M4 10h16" /></svg>;
  if (name === "search") return <svg {...common}><circle cx="10.5" cy="10.5" r="5.5" /><path d="m15 15 5 5" /></svg>;
  if (name === "star") return <svg {...common}><path d="m12 3 2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.9-5.4 2.9 1-6.1-4.4-4.3 6.1-.9L12 3Z" /></svg>;
  return <svg {...common}><circle cx="7" cy="7" r="2" /><circle cx="17" cy="7" r="2" /><circle cx="12" cy="17" r="2" /><path d="m8.7 8.2 2.2 6.6M15.3 8.2l-2.2 6.6M9 7h6" /></svg>;
}

function judgmentTone(judgment) {
  if (String(judgment).includes("중단")) return "border-[#FFB2A6] bg-[#FFF5F2] text-[#D9432F]";
  if (String(judgment).includes("약화")) return "border-[#F3D49B] bg-[#FFF8E9] text-[#A66A18]";
  return "border-[#B7D8C8] bg-[#EAF4EF] text-[#075C45]";
}

function ReviewerSplitList({
  reviewers,
  activeReviewerId,
  onSelect,
  multiSelect = false,
  selectedIds = new Set(),
  onToggleSelect,
  onToggleSelectAll,
  scope = "core",
}) {
  const allSelected = multiSelect && reviewers.length > 0 && reviewers.every((reviewer) => selectedIds.has(reviewer.userId));
  return (
    <div className="overflow-hidden rounded-xl border border-[#DDE4DF] bg-white shadow-[0_8px_24px_rgba(23,33,29,0.04)]">
      <div className={`grid ${ROW_GRID} min-h-11 min-w-[780px] items-center gap-3 border-b border-[#DDE4DF] bg-[#FAFBFA] px-3 text-[10px] font-black text-[#718078]`}>
        {multiSelect ? (
          <input type="checkbox" checked={allSelected} onChange={() => onToggleSelectAll(reviewers.map((reviewer) => reviewer.userId))} className="h-4 w-4 accent-[#075C45]" aria-label="현재 페이지 전체 선택" />
        ) : <span>선택</span>}
        <span>검토 ID</span>
        <span>우선순위</span>
        <span>위험 유형</span>
        <span>관찰 신호</span>
        <span>모델 판단</span>
        <span className="text-center">관리자 상태</span>
      </div>

      {reviewers.map((reviewer) => {
        const isActive = reviewer.userId === activeReviewerId;
        const completed = Boolean(reviewer.managerDecision);
        const observation = observationFor(reviewer, scope);
        return (
          <div
            key={reviewer.userId}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(reviewer)}
            onKeyDown={(event) => { if (event.key === "Enter") onSelect(reviewer); }}
            className={`grid ${ROW_GRID} min-h-[54px] min-w-[780px] w-full items-center gap-3 border-b border-[#EEF2EF] px-3 text-left text-xs transition last:border-b-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-inset focus-visible:outline-[#137A5A] ${isActive ? "bg-[#EDF6F1] shadow-[inset_3px_0_0_#137A5A]" : "hover:bg-[#F8FAF8]"}`}
          >
            {multiSelect ? (
              <input type="checkbox" checked={selectedIds.has(reviewer.userId)} onClick={(event) => event.stopPropagation()} onChange={() => onToggleSelect(reviewer.userId)} className="h-4 w-4 accent-[#075C45]" aria-label={`${reviewer.userId} 선택`} />
            ) : (
              <span className={`grid h-4 w-4 place-items-center rounded-full border ${isActive ? "border-[#137A5A]" : "border-[#C9D1CC]"}`}>
                {isActive && <span className="h-2 w-2 rounded-full bg-[#137A5A]" />}
              </span>
            )}
            <span className="truncate font-bold text-[#26312C]" title={reviewer.userId}>{reviewer.userId}</span>
            <span className="w-fit rounded-md bg-[#FFF4DE] px-2 py-1 font-black text-[#A66A18]">{reviewer.priorityRank}위</span>
            <span className="truncate text-[#4F5D56]" title={reviewer.riskType}>{reviewer.riskType}</span>
            <span className="flex min-w-0 items-center gap-2 font-medium text-[#3E4A44]" title={reviewer.coreChange || reviewer.coreSignal}><span className={`grid w-4 shrink-0 place-items-center ${observation.tone}`}><SignalIcon name={observation.icon} /></span><span className="truncate">{observation.label}</span></span>
            <span><span className={`inline-flex whitespace-nowrap rounded-md border px-2 py-1 text-[10px] font-bold ${judgmentTone(reviewer.modelJudgment)}`}>{reviewer.modelJudgment || "산정 불가"}</span></span>
            <span className="flex justify-center">
              <span className={`whitespace-nowrap rounded-md border px-2 py-1 text-[10px] font-bold ${completed ? (DECISION_TONES[reviewer.managerDecision] ?? "border-[#B7D8C8] bg-[#EAF4EF] text-[#075C45]") : "border-[#FF8C7A] bg-[#FFF5F2] text-[#E64A35]"}`}>
                {statusLabel(reviewer)}
              </span>
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default ReviewerSplitList;
