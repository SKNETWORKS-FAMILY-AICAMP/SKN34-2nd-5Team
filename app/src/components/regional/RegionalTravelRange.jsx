import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// Cohort reference lines from docs/05_feature_validation_report.md §7 —
// actual post-hoc outcome medians (retained 14.29km / lost 10.31km), not
// recomputed from predicted_state here. Recomputing from predictions would
// mix a forecast with a validated observation; these are fixed, cited
// values (work-spec §2.7 / A-7).
const COHORT_RETAINED_MEDIAN_KM = 14.29;
const COHORT_LOST_MEDIAN_KM = 10.31;
const MIN_SCALE_KM = 32;

function RegionalTravelRange() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/api/regional/radius`)
      .then((response) => {
        if (!response.ok) throw new Error(`탐방 범위 데이터를 불러오지 못했습니다 (${response.status})`);
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
  }, []);

  if (error) {
    return <p className="text-xs text-[#8A3B2E]">{error}</p>;
  }

  if (!data) {
    return <p className="text-xs text-[#626D67]">불러오는 중…</p>;
  }

  const maxQ3 = Math.max(
    COHORT_RETAINED_MEDIAN_KM,
    ...data.regions.map((region) => region.q3P90RadiusKm),
  );
  const scaleKm = Math.ceil(Math.max(MIN_SCALE_KM, maxQ3) / 10) * 10;
  const pct = (km) => `${Math.min(100, (km / scaleKm) * 100)}%`;

  return (
    <div className="rounded-lg border border-[#DDE4DF] bg-white p-2">
      <div className="grid grid-cols-[96px_1fr_50px_60px] gap-2 border-b border-[#DDE4DF] px-3 py-2 text-[11px] text-[#626D67]">
        <span>권역</span>
        <span className="flex justify-between"><span>0km</span><span>{scaleKm}km</span></span>
        <span className="text-right">중앙값</span>
        <span className="text-right">리뷰어</span>
      </div>

      <div>
        {data.regions.map((region) => (
          <div
            key={region.region}
            className={[
              "grid grid-cols-[96px_1fr_50px_60px] items-center gap-2 px-3 py-1.5 text-xs",
              region.belowMinimum ? "bg-[#FBF6EC]" : "",
            ].join(" ")}
          >
            <span>{region.region}</span>
            <div className="relative h-4">
              <div
                className="pointer-events-none absolute inset-y-0 z-10 w-px bg-[#E7B8AE]"
                style={{ left: pct(COHORT_LOST_MEDIAN_KM) }}
                title={`상실 코호트 참고 중앙값 ${COHORT_LOST_MEDIAN_KM}km`}
              />
              <div
                className="pointer-events-none absolute inset-y-0 z-10 w-px bg-[#8DB9A4]"
                style={{ left: pct(COHORT_RETAINED_MEDIAN_KM) }}
                title={`유지 코호트 참고 중앙값 ${COHORT_RETAINED_MEDIAN_KM}km`}
              />
              <div
                className="absolute top-1 h-2.5 rounded-sm"
                style={{
                  left: pct(region.q1P90RadiusKm),
                  right: `calc(100% - ${pct(region.q3P90RadiusKm)})`,
                  background: region.belowMinimum ? "#EBDCC2" : "#CFE0D6",
                }}
              />
              <div
                className="absolute top-0 h-4 w-0.5"
                style={{
                  left: pct(region.medianP90RadiusKm),
                  background: region.belowMinimum ? "#A66A18" : "#137A5A",
                }}
              />
            </div>
            <span
              className={`text-right ${region.belowMinimum ? "text-[#A66A18]" : ""}`}
            >
              {region.medianP90RadiusKm}km
            </span>
            <span className={`text-right ${region.belowMinimum ? "text-[#A66A18]" : "text-[#626D67]"}`}>
              {region.reviewers.toLocaleString()}
            </span>
          </div>
        ))}
      </div>

      <p className="border-t border-[#DDE4DF] px-3 py-2 text-[11px] text-[#626D67]">
        띠 = 사분위 범위(Q1~Q3) · 세로선 = 중앙값 · 표본이 작은 권역(주황)은 띠가 넓어 중앙값을 단정하기 어렵습니다 · 코호트 실제 중앙값 참고선 — 상실{" "}
        {COHORT_LOST_MEDIAN_KM}km / 유지 {COHORT_RETAINED_MEDIAN_KM}km · 반경 계산 제외 {data.excludedReviewers?.toLocaleString() ?? 0}명
      </p>
      <p className="px-3 pb-2 text-[11px] text-[#626D67]">
        탐방 반경은 음식점 밀도와 도시 규모에 좌우되며 v04 위험 예측 피처가 아닙니다 — 캠페인 거리 범위를 정하는 권역 특성으로만 사용합니다.
      </p>
    </div>
  );
}

export default RegionalTravelRange;
