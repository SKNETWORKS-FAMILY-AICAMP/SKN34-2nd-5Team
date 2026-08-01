// 14 fixed city coordinates (relative layout, not real lat/long projection —
// see docs/ui/V05_WORK_SPEC.md §2.4 for why a state choropleth or albersUsa
// projection doesn't work here: AB is Alberta, Canada, and PA/NJ/DE plus
// MO/IL are the same metro split across state lines). No map library, no
// tile server — just positioned circles.
const CITY_POSITIONS = {
  PA: { cx: 576, cy: 139 },
  NJ: { cx: 604, cy: 118 },
  DE: { cx: 604, cy: 158 },
  FL: { cx: 496, cy: 222 },
  IN: { cx: 455, cy: 138 },
  TN: { cx: 448, cy: 164 },
  LA: { cx: 412, cy: 204 },
  MO: { cx: 411, cy: 148 },
  IL: { cx: 434, cy: 166 },
  AZ: { cx: 182, cy: 190 },
  NV: { cx: 84, cy: 140 },
  ID: { cx: 124, cy: 112 },
  CA: { cx: 85, cy: 174 },
  AB: { cx: 154, cy: 42 },
};

function radiusFor(reviewers) {
  return Math.max(5, 4 + Math.sqrt(reviewers) / 3);
}

function fillFor(highRiskRate) {
  if (highRiskRate >= 0.7) return { fill: "#E15D47", stroke: "#B4402F" };
  if (highRiskRate >= 0.6) return { fill: "#DFA94A", stroke: "#A66A18" };
  return { fill: "#B7CFC2", stroke: "#7FA894" };
}

function RegionalBubbleMap({ regions, hoveredRegion, onHoverRegion }) {
  return (
    <div className="rounded-lg border border-[#DDE4DF] bg-white p-2">
      <p className="px-2 pt-1 text-[11px] text-[#626D67]">
        위치 모식도 — 실제 국경·해안선이 아닌 상대 배치입니다
      </p>

      <svg
        viewBox="0 0 660 260"
        className="w-full"
        role="img"
        aria-label="14개 대표 도시를 활동 리뷰어 수(원 크기)와 고위험 비율(원 색)로 표시한 위치 모식도"
      >
        <line x1="30" y1="72" x2="640" y2="72" stroke="#C6CFC9" strokeWidth="1" strokeDasharray="5 4" />
        <text x="34" y="66" fill="#626D67" fontSize="10">
          미국–캐나다 국경
        </text>

        <ellipse cx={588} cy={140} rx={46} ry={36} fill="none" stroke="#137A5A" strokeWidth="1" strokeDasharray="4 4" />
        <text x={588} y={94} textAnchor="middle" fill="#137A5A" fontSize="10">
          필라델피아 광역{" "}
          {(
            (regions.find((r) => r.region === "PA")?.reviewers ?? 0) +
            (regions.find((r) => r.region === "NJ")?.reviewers ?? 0) +
            (regions.find((r) => r.region === "DE")?.reviewers ?? 0)
          ).toLocaleString()}
          명
        </text>

        <ellipse cx={424} cy={158} rx={34} ry={26} fill="none" stroke="#137A5A" strokeWidth="1" strokeDasharray="4 4" />
        <text x={424} y={196} textAnchor="middle" fill="#137A5A" fontSize="10">
          세인트루이스 광역{" "}
          {(
            (regions.find((r) => r.region === "MO")?.reviewers ?? 0) +
            (regions.find((r) => r.region === "IL")?.reviewers ?? 0)
          ).toLocaleString()}
          명
        </text>

        {regions.map((region) => {
          const pos = CITY_POSITIONS[region.region];
          if (!pos) return null;

          const r = radiusFor(region.reviewers);
          const { fill, stroke } = fillFor(region.highRiskRate);
          const isHovered = hoveredRegion === region.region;

          return (
            <g
              key={region.region}
              onMouseEnter={() => onHoverRegion(region.region)}
              onMouseLeave={() => onHoverRegion(null)}
              className="cursor-pointer"
            >
              <circle
                cx={pos.cx}
                cy={pos.cy}
                r={r}
                fill={fill}
                stroke={stroke}
                strokeWidth={isHovered ? 2.5 : 1}
              />
              <text
                x={pos.cx}
                y={pos.cy + 3}
                textAnchor="middle"
                fontSize={r > 12 ? 11 : 9}
                fill={region.highRiskRate >= 0.7 ? "#fff" : "#17211D"}
              >
                {region.region}
              </text>
              {isHovered && (
                <text x={pos.cx} y={pos.cy - r - 4} textAnchor="middle" fontSize="10" fill="#17211D">
                  {region.topCity} · {region.reviewers.toLocaleString()}명 ·{" "}
                  {(region.highRiskRate * 100).toFixed(1)}%
                </text>
              )}
            </g>
          );
        })}

        <g>
          <circle cx={40} cy={244} r={13} fill="none" stroke="#B3BBB6" />
          <text x={66} y={248} fill="#626D67" fontSize="10">
            원 크기 = 활동 리뷰어 수
          </text>
          <circle cx={270} cy={244} r={6} fill="#B7CFC2" stroke="#7FA894" />
          <text x={284} y={248} fill="#626D67" fontSize="10">
            고위험 60% 미만
          </text>
          <circle cx={400} cy={244} r={6} fill="#DFA94A" stroke="#A66A18" />
          <text x={414} y={248} fill="#626D67" fontSize="10">
            60~70%
          </text>
          <circle cx={500} cy={244} r={6} fill="#E15D47" stroke="#B4402F" />
          <text x={514} y={248} fill="#626D67" fontSize="10">
            70% 이상 · 고위험 비율
          </text>
        </g>
      </svg>
    </div>
  );
}

export default RegionalBubbleMap;
