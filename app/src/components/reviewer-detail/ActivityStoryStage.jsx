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

function BarEncoding({ before, after, max }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-2.5 rounded-sm bg-[#B7CFC2]" style={{ width: `${(before / max) * 100}%`, minWidth: 4 }} />
      <div className="h-2.5 rounded-sm bg-[#137A5A]" style={{ width: `${(after / max) * 100}%`, minWidth: 4 }} />
    </div>
  );
}

function DotEncoding({ before, after }) {
  return (
    <div className="flex items-center gap-1">
      <span className="flex gap-0.5 text-[#B7CFC2]">
        {Array.from({ length: Math.min(before, 12) }, (_, i) => (
          <span key={i}>●</span>
        ))}
      </span>
      <span className="text-[#B3BBB6]">→</span>
      <span className="flex gap-0.5 text-[#137A5A]">
        {Array.from({ length: Math.min(after, 12) }, (_, i) => (
          <span key={i}>●</span>
        ))}
      </span>
    </div>
  );
}

function TickEncoding({ before, after, max }) {
  return (
    <div className="relative h-4 flex-1 border-b border-[#DDE4DF]">
      <span
        className="absolute top-0.5 h-2 w-0.5 bg-[#B7CFC2]"
        style={{ left: `${(before / max) * 100}%` }}
      />
      <span
        className="absolute top-0.5 h-2 w-0.5 bg-[#137A5A]"
        style={{ left: `${(after / max) * 100}%` }}
      />
    </div>
  );
}

function DiamondEncoding({ before, after }) {
  return (
    <div className="flex items-center gap-1">
      <span className="flex gap-0.5 text-[#B7CFC2]">
        {Array.from({ length: Math.min(before, 10) }, (_, i) => (
          <span key={i}>◆</span>
        ))}
      </span>
      <span className="text-[#B3BBB6]">→</span>
      <span className="flex gap-0.5 text-[#137A5A]">
        {Array.from({ length: Math.min(after, 10) }, (_, i) => (
          <span key={i}>◆</span>
        ))}
      </span>
    </div>
  );
}

const encodings = [BarEncoding, DotEncoding, TickEncoding, DiamondEncoding];

function ActivityStoryStage({ changes, comparisonYear, selectionYear, highlightedLabels }) {
  if (changes.length === 0) return null;

  const strongest = [...changes].sort((a, b) => {
    const magA = Math.abs(parseNumber(a.delta) ?? 0);
    const magB = Math.abs(parseNumber(b.delta) ?? 0);
    return magB - magA;
  })[0];

  return (
    <div className="rounded-lg border border-[#DDE4DF] bg-white p-4">
      <p className="text-sm font-medium text-[#17211D]">
        {comparisonYear} → {selectionYear} 활동 변화
      </p>

      <div className="mt-2 grid grid-cols-[110px_1fr_90px] gap-3 border-b border-[#DDE4DF] pb-2 text-[11px] text-[#626D67]">
        <span />
        <span>
          {comparisonYear} 비교 —————————— {selectionYear} 선정
        </span>
        <span className="text-right">변화</span>
      </div>

      {changes.map((change, index) => {
        const Encoding = encodings[index % encodings.length];
        const before = parseNumber(change.before);
        const after = parseNumber(change.after);
        const canEncode = before !== null && after !== null;
        const max = canEncode ? Math.max(before, after, 1) : 1;

        const isHighlighted = highlightedLabels?.includes(change.label);

        return (
          <div
            key={change.label}
            className={`grid grid-cols-[110px_1fr_90px] items-center gap-3 py-2 text-xs transition ${
              isHighlighted
                ? "bg-[#E3F1EA] -mx-1 px-1 rounded"
                : index % 2 === 0
                  ? "bg-[#F6F8F6] -mx-1 px-1 rounded"
                  : "-mx-1 px-1 rounded"
            }`}
          >
            <span className="text-[#626D67]">{change.label}</span>

            {canEncode ? (
              <Encoding before={before} after={after} max={max} />
            ) : (
              <span className="text-[#626D67]">
                {change.before} → {change.after}
              </span>
            )}

            <span
              className="text-right font-medium"
              style={{ color: toneColor(change.tone) }}
            >
              {change.delta}
            </span>
          </div>
        );
      })}

      {strongest && (
        <p className="mt-2.5 rounded bg-[#F7F8F5] px-2.5 py-2 text-xs">
          가장 큰 변화 —{" "}
          <strong className="font-medium">
            {strongest.label} {strongest.delta}
          </strong>
        </p>
      )}
    </div>
  );
}

export default ActivityStoryStage;
