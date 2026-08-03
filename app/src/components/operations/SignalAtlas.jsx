import { useMemo } from "react";
import { useNavigate } from "react-router";

// Recency bin edges in days — validated against the actual v04 cohort
// distribution (31.6% / 29.7% / 19.8% / 14.3% / 4.5% across the five bins),
// not evenly spaced but not extreme enough to need rebalancing either.
const RECENCY_BINS = [
  { min: 0, max: 15, label: "0–15일" },
  { min: 15, max: 45, label: "15–45일" },
  { min: 45, max: 90, label: "45–90일" },
  { min: 90, max: 180, label: "90–180일" },
  { min: 180, max: Infinity, label: "180일+" },
];

// recentActiveMonths only ever takes integer values 3–12 in this cohort
// (power-reviewer minimum activity requirement), never 0 or partial.
const MONTH_ROWS = [12, 11, 10, 9, 8, 7, 6, 5, 4, 3];

function recencyBinIndex(days) {
  return RECENCY_BINS.findIndex((bin) => days >= bin.min && days < bin.max);
}

// Fill = crmTarget rate (this screen's own question: where should I look
// first). Border = cells where that rate is the majority outcome, not a
// judgment call about the person, just where the aggregate leans.
function fillFor(rate) {
  if (rate >= 0.9) return { bg: "#E15D47", text: "#17211D" };
  if (rate >= 0.7) return { bg: "#E86A54", text: "#17211D" };
  if (rate >= 0.4) return { bg: "#E6B26F", text: "#5C3A0E" };
  if (rate >= 0.2) return { bg: "#E9C48A", text: "#5C3A0E" };
  if (rate >= 0.1) return { bg: "#C5DFCF", text: "#17211D" };
  if (rate >= 0.03) return { bg: "#A9C8B7", text: "#17211D" };
  if (rate > 0) return { bg: "#B7CFC2", text: "#17211D" };
  return { bg: "#E8EDE9", text: "#626D67" };
}

function SignalAtlas({ reviewers }) {
  const navigate = useNavigate();

  const grid = useMemo(() => {
    const cells = new Map();

    reviewers.forEach((reviewer) => {
      const binIndex = recencyBinIndex(reviewer.recentRecencyDays);
      if (binIndex === -1) return;

      const key = `${reviewer.recentActiveMonths}|${binIndex}`;
      const cell = cells.get(key) ?? { total: 0, target: 0 };
      cell.total += 1;
      if (reviewer.crmTarget) cell.target += 1;
      cells.set(key, cell);
    });

    return cells;
  }, [reviewers]);

  // Trust signal, not decoration — confirms the grid isn't silently
  // dropping reviewers whose recentRecencyDays falls outside every bin.
  const coveredCount = useMemo(
    () => [...grid.values()].reduce((sum, cell) => sum + cell.total, 0),
    [grid],
  );

  function goToBin(months, binIndex) {
    const bin = RECENCY_BINS[binIndex];
    const params = new URLSearchParams({
      recencyMin: String(bin.min),
      recencyMax: Number.isFinite(bin.max) ? String(bin.max) : "",
      activeMonths: String(months),
    });
    navigate(`/reviewers?${params.toString()}`);
  }

  return (
    <div className="rounded-lg border border-[#DDE4DF] bg-white p-4">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-medium text-[#17211D]">
          오늘 먼저 볼 신호
        </p>
        <span className="text-xs text-[#626D67]">
          클릭 시 해당 조건으로 리뷰어 관리 필터링
        </span>
      </div>

      <p className="mt-1 text-[11px] text-[#626D67]">
        세로 = 최근 활동 개월 수(12→3, 아래로 갈수록 활동 적음) · 가로 = 마지막
        리뷰 후 경과일
      </p>

      <div
        className="mt-3 grid gap-[3px]"
        style={{ gridTemplateColumns: "56px repeat(5, 1fr)" }}
      >
        <span />
        {RECENCY_BINS.map((bin) => (
          <span
            key={bin.label}
            className="pb-1 text-center text-[11px] text-[#626D67]"
          >
            {bin.label}
          </span>
        ))}

        {MONTH_ROWS.map((months) => (
          <FragmentRow
            key={months}
            months={months}
            grid={grid}
            onCellClick={goToBin}
          />
        ))}
      </div>

      <p className="mt-1.5 text-[11px] text-[#626D67]">
        격자에 포함된 리뷰어 {coveredCount.toLocaleString()}명 / 전체{" "}
        {reviewers.length.toLocaleString()}명
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-4 text-[11px] text-[#626D67]">
        <span>셀 = 이 조합에 속한 인원(n)과 검토 대상 비율</span>
        <span className="flex items-center gap-1.5">
          <span
            className="h-3.5 w-3.5 rounded-sm"
            style={{
              background: "#E86A54",
              outline: "2px solid #17211D",
              outlineOffset: "-2px",
            }}
          />
          굵은 테두리 = 검토 대상 비율 50% 이상
        </span>
        <span>— = 이 조합에 해당하는 리뷰어 없음</span>
      </div>

      <div className="mt-2 flex items-center gap-2 text-[11px] text-[#626D67]">
        <span>검토 대상 비율</span>
        <span>낮음</span>
        <span
          className="h-2.5 w-32 rounded-full"
          style={{
            background:
              "linear-gradient(to right, #E8EDE9, #B7CFC2, #A9C8B7, #C5DFCF, #E9C48A, #E6B26F, #E86A54, #E15D47)",
          }}
        />
        <span>높음</span>
      </div>

      <p
        className="mt-2 text-[11px] text-[#626D67]"
        title="risk_score와 통합 우선순위는 보정된 확률이 아니라 상대적 검토 순위입니다."
      >
        관찰된 활동 신호의 밀집도이며 개별 확률이 아닙니다 ⓘ
      </p>
    </div>
  );
}

function FragmentRow({ months, grid, onCellClick }) {
  return (
    <>
      <span className="flex items-center justify-end pr-1.5 text-[11px] text-[#626D67]">
        {months}개월
      </span>

      {RECENCY_BINS.map((bin, binIndex) => {
        const cell = grid.get(`${months}|${binIndex}`);

        if (!cell) {
          return (
            <div
              key={bin.label}
              className="flex items-center justify-center rounded-sm bg-[#F1F4F1] text-[#B3BBB6]"
              style={{ aspectRatio: "2.6" }}
            >
              —
            </div>
          );
        }

        const rate = cell.target / cell.total;
        const { bg, text } = fillFor(rate);
        const highlighted = rate >= 0.5;

        return (
          <button
            key={bin.label}
            type="button"
            onClick={() => onCellClick(months, binIndex)}
            className="flex flex-col items-center justify-center gap-px rounded-sm text-[11px] transition hover:brightness-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[#17211D]"
            style={{
              aspectRatio: "2.6",
              background: bg,
              color: text,
              outline: highlighted ? "2px solid #17211D" : undefined,
              outlineOffset: highlighted ? "-2px" : undefined,
            }}
          >
            <b className="text-[13px] font-medium">
              {Math.round(rate * 100)}%
            </b>
            <span>n={cell.total}</span>
          </button>
        );
      })}
    </>
  );
}

export default SignalAtlas;
