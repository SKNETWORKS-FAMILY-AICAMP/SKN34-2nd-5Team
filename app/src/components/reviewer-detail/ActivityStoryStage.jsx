// Distinct visual encoding per row (bar / dots / tick scale / diamonds),
// cycling by index, so scanning several metrics doesn't read as one
// repeated shape. `changes` items are {label, before, after, delta, tone}
// from the API — before/after are pre-formatted strings ("31건", "9개월"),
// so magnitude is only drawn when a leading number can be parsed; otherwise
// the row falls back to text only rather than guessing a bar length.
function parseNumber(value) {
  const match = String(value).match(/[\d,.]+/);
  if (!match) return null;
  const parsed = Number(match[0].replaceAll(",", ""));
  return Number.isFinite(parsed) ? parsed : null;
}

function toneColor(tone) {
  if (tone === "positive") return "#137A5A";
  if (tone === "muted") return "#626D67";
  return "#BF3620";
}

function FixedTrack({ tone }) {
  const endColor = toneColor(tone);
  return (
    <div className="relative mt-1 h-2.5 w-full" aria-hidden="true">
      <span className="absolute left-1 right-1 top-1 h-0.5 bg-[#DDE4DF]" />
      <span className="absolute left-0 top-0 h-2.5 w-2.5 rounded-full border-2 border-white bg-[#AFC8BB] shadow-sm" />
      <span className="absolute right-0 top-0 h-2.5 w-2.5 rounded-full border-2 border-white shadow-sm" style={{ backgroundColor: endColor }} />
    </div>
  );
}

// Same 150-day threshold insights.py's risk_signals() already surfaces in
// the "마지막 리뷰 공백" evidence line — not a new baseline, just reused here
// so the snapshot card reads consistently with the evidence panel.
const RECENCY_BASELINE_DAYS = 150;
const MONTHS_PER_YEAR = 12;

const METRIC_GLYPHS = {
  "리뷰 수": "▤",
  "활동 월": "▦",
  "고유 음식점": "⌂",
  "리뷰 공백": "◷",
};

function MetricGlyph({ label, risk = false }) {
  return (
    <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-lg text-sm font-black ${risk ? "bg-[#FDE3DD] text-[#BF3620]" : "bg-[#E3F1EA] text-[#075C45]"}`} aria-hidden="true">
      {METRIC_GLYPHS[label] ?? "•"}
    </span>
  );
}

function SnapshotCard({ title, value, unit, caption, children, risk = false }) {
  return (
    <div className={`rounded-xl border p-3.5 ${risk ? "border-[#F1A999] bg-[#FFF4F1]" : "border-[#DDE4DF] bg-[linear-gradient(145deg,#FFFFFF,#F5F8F6)]"}`}>
      <div className="flex items-center gap-2"><MetricGlyph label={title.replace("최근 ", "")} risk={risk} /><p className={`text-[11px] font-bold ${risk ? "text-[#A83422]" : "text-[#4F5D56]"}`}>{title}</p></div>
      <p className={`mt-2 text-2xl font-black ${risk ? "text-[#BF3620]" : "text-[#17211D]"}`}>
        {value}
        {unit && <span className="ml-0.5 text-sm font-normal text-[#626D67]">{unit}</span>}
      </p>
      {children}
      {caption && <p className="mt-1.5 text-[11px] text-[#626D67]">{caption}</p>}
    </div>
  );
}

function MonthDots({ activeMonths }) {
  return (
    <span className="mt-1.5 flex gap-0.5">
      {Array.from({ length: MONTHS_PER_YEAR }, (_, i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full"
          style={{ background: i < activeMonths ? "#137A5A" : "#DDE4DF" }}
        />
      ))}
    </span>
  );
}

// insights.py's risk_signals() title -> the changes[] label it corresponds
// to. "평균 작성 간격" has no entry here since it's only in intervalComparison,
// not changes — a lookup miss there just falls through to the next evidence
// item rather than crashing.
const EVIDENCE_TITLE_TO_CHANGE_LABEL = {
  "최근 활동 지속성": "활동 월",
  "리뷰 생산량": "리뷰 수",
  "마지막 리뷰 공백": "리뷰 공백",
  "음식점 탐색량": "고유 음식점",
};

function ActivityStoryStage({
  changes,
  comparisonYear,
  selectionYear,
  highlightedLabels,
  priorActivityAvailable = true,
  evidence = [],
}) {
  if (changes.length === 0) return null;

  const byLabel = Object.fromEntries(changes.map((change) => [change.label, change]));

  if (!priorActivityAvailable) {
    const reviewCount = parseNumber(byLabel["리뷰 수"]?.after);
    const activeMonths = parseNumber(byLabel["활동 월"]?.after);
    const uniqueBusinesses = parseNumber(byLabel["고유 음식점"]?.after);
    const recencyDays = parseNumber(byLabel["리뷰 공백"]?.after);

    return (
      <div className="rounded-lg border border-[#DDE4DF] bg-white p-4">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-[#17211D]">{selectionYear}년 활동 현황</p>
          <span className="rounded bg-[#F1F4F1] px-1.5 py-0.5 text-[10px] text-[#626D67]">
            {comparisonYear}년 비교 기록 없음
          </span>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-2.5 xl:grid-cols-4">
          {reviewCount !== null && (
            <SnapshotCard title="리뷰 수" value={reviewCount} unit="건" caption={`${selectionYear}년 관찰값`} />
          )}
          {activeMonths !== null && (
            <SnapshotCard
              title="활동 월"
              value={`${activeMonths}/${MONTHS_PER_YEAR}`}
              unit="개월"
            >
              <MonthDots activeMonths={activeMonths} />
            </SnapshotCard>
          )}
          {uniqueBusinesses !== null && (
            <SnapshotCard title="고유 음식점" value={uniqueBusinesses} unit="곳" caption="음식점 탐색 규모" />
          )}
          {recencyDays !== null && (
            <SnapshotCard
              title="최근 리뷰 공백"
              value={recencyDays}
              unit="일"
              caption={recencyDays >= RECENCY_BASELINE_DAYS ? `기준선 ${RECENCY_BASELINE_DAYS}일 초과` : undefined}
              risk={recencyDays >= RECENCY_BASELINE_DAYS}
            />
          )}
        </div>

        <p className="mt-3 text-[11px] text-[#626D67]">
          {comparisonYear}년 활동 기록이 없어 전년 대비 증감률은 계산하지 않았습니다.
        </p>
      </div>
    );
  }

  const leadEvidence = evidence.find(
    (item) => EVIDENCE_TITLE_TO_CHANGE_LABEL[item.title] in byLabel,
  );
  const leadChange = leadEvidence ? byLabel[EVIDENCE_TITLE_TO_CHANGE_LABEL[leadEvidence.title]] : null;

  return (
    <div className="overflow-hidden rounded-xl border border-[#DDE4DF] bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E2E7E3] px-4 py-2.5">
        <div><p className="text-[9px] font-black tracking-[0.12em] text-[#137A5A]">ACTIVITY EVIDENCE</p><p className="mt-0.5 text-sm font-black text-[#17211D]">{comparisonYear} → {selectionYear} 활동 변화</p></div>
        <div className="flex items-center gap-4 text-[11px] text-[#626D67]"><span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-[#B7CFC2]" />{comparisonYear} 비교</span><span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-[#075C45]" />{selectionYear} 선정</span></div>
      </div>

      <div className="grid gap-2.5 p-3 sm:grid-cols-2 2xl:grid-cols-4">
      {changes.map((change, index) => {
        const before = parseNumber(change.before);
        const after = parseNumber(change.after);
        const canEncode = before !== null && after !== null;

        const isHighlighted = highlightedLabels?.includes(change.label);
        const isLead = leadChange?.label === change.label;

        return (
          <div
            key={change.label}
            className={`min-w-0 rounded-xl border px-3.5 py-3 text-xs shadow-[0_3px_10px_rgba(23,33,29,0.035)] transition ${
              isHighlighted
                ? "border-[#75A98F] bg-[#E3F1EA]"
                : isLead
                  ? "border-[#F1B7AB] bg-[#FFF5F2]"
                  : index % 2 === 0 ? "border-[#E1E8E4] bg-[linear-gradient(145deg,#FFFFFF,#F5F8F6)]" : "border-[#E1E8E4] bg-white"
            }`}
          >
            <span className="flex items-center justify-between gap-2">
              <span className={`flex items-center gap-2 font-bold ${isLead ? "text-[#B93D29]" : "text-[#4F5D56]"}`}><MetricGlyph label={change.label} risk={isLead} />{change.label}</span>
              <span className={`rounded-full px-2 py-1 text-[10px] font-black ${isLead ? "bg-[#FDE3DD]" : "bg-[#EDF5F1]"}`} style={{ color: toneColor(change.tone) }}>{change.delta}</span>
            </span>

            <span className="mt-3 flex min-w-0 flex-col gap-2">
              <span className="flex items-center justify-between gap-2"><span><small className="block text-[9px] text-[#7B8780]">{comparisonYear}</small><strong className="text-base text-[#4F5D56]">{change.before}</strong></span><span className="text-sm font-black text-[#9AA39E]">→</span><span className="text-right"><small className="block text-[9px] text-[#7B8780]">{selectionYear}</small><strong className={`text-base ${isLead ? "text-[#BF3620]" : "text-[#075C45]"}`}>{change.after}</strong></span></span>
              {canEncode && <FixedTrack tone={change.tone} />}
            </span>
            {isLead && <p className="mt-2 border-t border-[#F2C6BC] pt-2 text-[10px] font-bold text-[#A83422]">핵심 위험 변화 · 우선 확인 필요</p>}
          </div>
        );
      })}

      </div>
    </div>
  );
}

export default ActivityStoryStage;
