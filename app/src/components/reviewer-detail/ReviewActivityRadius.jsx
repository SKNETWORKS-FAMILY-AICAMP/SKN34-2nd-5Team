import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Circles are capped at this many km so one distant outlier (a travel
// review) doesn't shrink the entire local cluster to invisibility — real
// v04 data has exactly this case (a Tampa-centered reviewer with four
// New Orleans reviews ~765km out). Points beyond the cap go in the
// out-of-scale inset instead of being silently dropped.
const SCALE_CAP_KM = 40;

const VIEWPORT_PX = 320;
const CENTER_PX = VIEWPORT_PX / 2;
const RENDER_RADIUS_PX = 130;

function toXY(distanceKm, bearingDeg, pxPerKm) {
  const rad = (bearingDeg * Math.PI) / 180;
  return {
    x: CENTER_PX + distanceKm * pxPerKm * Math.sin(rad),
    y: CENTER_PX - distanceKm * pxPerKm * Math.cos(rad),
  };
}

function ReviewActivityRadius({ userId }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/api/reviewer-details/${encodeURIComponent(userId)}/radius`)
      .then((response) => {
        if (!response.ok) throw new Error(`반경 데이터를 불러오지 못했습니다 (${response.status})`);
        return response.json();
      })
      .then((json) => {
        if (active) setData(json);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [userId]);

  if (error) {
    return (
      <div className="rounded-lg border border-[#DDE4DF] bg-white p-4 text-xs text-[#8A3B2E]">
        {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-lg border border-[#DDE4DF] bg-white p-4 text-xs text-[#626D67]">
        불러오는 중…
      </div>
    );
  }

  if (!data.available || (!data.comparison?.available && !data.selection?.available)) {
    return (
      <div className="rounded-lg border border-[#DDE4DF] bg-white p-4">
        <p className="text-sm font-medium text-[#17211D]">리뷰 활동 반경</p>
        <p className="mt-2 text-xs text-[#626D67]">
          이 리뷰어는 활동 음식점이 2곳 미만이라 반경을 계산할 수 없습니다.
        </p>
      </div>
    );
  }

  const { comparison, selection, change } = data;
  const scaleKm = Math.min(
    SCALE_CAP_KM,
    Math.max(comparison?.p90RadiusKm ?? 0, selection?.p90RadiusKm ?? 0, 5),
  );
  const pxPerKm = RENDER_RADIUS_PX / scaleKm;
  const scaleBarKm = Math.min(10, scaleKm);

  const withScale = (period) => {
    if (!period?.available) return { inScale: [], outOfScale: [] };
    const inScale = [];
    const outOfScale = [];
    for (const business of period.businesses) {
      (business.distanceKm <= scaleKm ? inScale : outOfScale).push(business);
    }
    return { inScale, outOfScale };
  };

  const comparisonPoints = withScale(comparison);
  const selectionPoints = withScale(selection);
  const outOfScale = [
    ...comparisonPoints.outOfScale.map((business) => ({
      ...business,
      activityYear: comparison.activityYear,
    })),
    ...selectionPoints.outOfScale.map((business) => ({
      ...business,
      activityYear: selection.activityYear,
    })),
  ];

  const comparisonRadiusPx = comparison?.available
    ? Math.min(comparison.p90RadiusKm, scaleKm) * pxPerKm
    : null;
  const selectionRadiusPx = selection?.available
    ? Math.min(selection.p90RadiusKm, scaleKm) * pxPerKm
    : null;

  return (
    <div className="rounded-lg border border-[#DDE4DF] bg-white p-4">
      <p className="text-sm font-medium text-[#17211D]">리뷰 활동 반경</p>
      <p className="mt-1 text-xs text-[#626D67]">
        {comparison?.available && selection?.available
          ? `${comparison.activityYear}년 반경 ${comparison.p90RadiusKm}km → ${selection.activityYear}년 반경 ${selection.p90RadiusKm}km`
          : selection?.available
            ? `${selection.activityYear}년 반경 ${selection.p90RadiusKm}km`
            : ""}
      </p>

      <div className="mt-3 flex flex-col gap-3 sm:flex-row">
        <svg
          viewBox={`0 0 ${VIEWPORT_PX} ${VIEWPORT_PX}`}
          className="h-auto w-full max-w-[320px] shrink-0 self-center"
          role="img"
          aria-label="리뷰 활동 반경을 중심 기준 상대 거리로 표시한 산점도. 절대 좌표는 표시하지 않습니다."
        >
          <line x1={CENTER_PX - 6} y1={CENTER_PX} x2={CENTER_PX + 6} y2={CENTER_PX} stroke="#B3BBB6" />
          <line x1={CENTER_PX} y1={CENTER_PX - 6} x2={CENTER_PX} y2={CENTER_PX + 6} stroke="#B3BBB6" />

          {comparisonRadiusPx !== null && (
            <circle
              cx={CENTER_PX}
              cy={CENTER_PX}
              r={comparisonRadiusPx}
              fill="none"
              stroke="#A66A18"
              strokeWidth="1.5"
              strokeDasharray="5 4"
            />
          )}
          {selectionRadiusPx !== null && (
            <circle
              cx={CENTER_PX}
              cy={CENTER_PX}
              r={selectionRadiusPx}
              fill="#E3F1EA"
              fillOpacity="0.8"
              stroke="#137A5A"
              strokeWidth="1.5"
            />
          )}

          {comparisonPoints.inScale.map((business, index) => {
            const { x, y } = toXY(business.distanceKm, business.bearingDeg, pxPerKm);
            return (
              <circle
                key={`c-${index}`}
                cx={x}
                cy={y}
                r="3.5"
                fill="#fff"
                stroke="#A66A18"
                strokeWidth="1.5"
              >
                <title>{`${comparison.activityYear}년 · ${business.name} · ${business.city} · ${business.distanceKm}km`}</title>
              </circle>
            );
          })}
          {selectionPoints.inScale.map((business, index) => {
            const { x, y } = toXY(business.distanceKm, business.bearingDeg, pxPerKm);
            return (
              <circle key={`s-${index}`} cx={x} cy={y} r="3.5" fill="#137A5A">
                <title>{`${selection.activityYear}년 · ${business.name} · ${business.city} · ${business.distanceKm}km`}</title>
              </circle>
            );
          })}

          <text x={CENTER_PX} y={16} textAnchor="middle" fill="#A66A18" fontSize="11">
            {comparison?.available ? `${comparison.activityYear}년 반경 ${comparison.p90RadiusKm}km` : ""}
          </text>
          <text x={CENTER_PX} y={VIEWPORT_PX - 8} textAnchor="middle" fill="#137A5A" fontSize="11">
            {selection?.available ? `${selection.activityYear}년 반경 ${selection.p90RadiusKm}km` : ""}
          </text>

          <line x1={20} y1={VIEWPORT_PX - 30} x2={20 + scaleBarKm * pxPerKm} y2={VIEWPORT_PX - 30} stroke="#626D67" />
          <text x={20} y={VIEWPORT_PX - 36} fill="#626D67" fontSize="10">
            {scaleBarKm}km · 상대 거리
          </text>
        </svg>

        <div className="min-w-0 flex-1">
          {outOfScale.length > 0 ? (
            <div className="rounded border border-dashed border-[#DDE4DF] p-2.5">
              <p className="text-xs font-medium text-[#17211D]">
                반경 밖 활동 · {outOfScale.length}곳
              </p>
              <ul className="mt-1.5 space-y-1">
                {outOfScale.map((business, index) => (
                  <li key={index} className="text-[11px] text-[#626D67]">
                    {business.activityYear}년 · {business.city} · 약 {Math.round(business.distanceKm)}km
                  </li>
                ))}
              </ul>
              <p className="mt-1.5 text-[11px] text-[#626D67]">
                축척 밖 원거리 활동입니다. P90 정의상 일부 활동은 원 밖에 위치할 수 있으므로 활동 맥락을 확인하세요.
              </p>
            </div>
          ) : (
            <p className="text-xs text-[#626D67]">반경 밖 활동 없음</p>
          )}

          {change && (
            <div className="mt-2.5 rounded bg-[#F7F8F5] p-2.5">
              <p className="text-[11px] text-[#626D67]">
                활동 중심 이동 {change.centerShiftKm ?? "—"}km
                {change.radiusChangeKm !== null && ` · 반경 변화 ${change.radiusChangeKm > 0 ? "+" : ""}${change.radiusChangeKm}km`}
              </p>
            </div>
          )}
        </div>
      </div>

      <p className="mt-3 text-[11px] leading-5 text-[#626D67]">
        각 기간의 중심점을 원점으로 다시 배치한 상대 분포입니다.
        <br />
        리뷰 활동 지역이며 거주지·직장·생활권을 나타내지 않습니다.
        <br />
        반경 축소는 v04 검증에서 위험 예측 피처로 채택되지 않았습니다.
      </p>
    </div>
  );
}

export default ReviewActivityRadius;
