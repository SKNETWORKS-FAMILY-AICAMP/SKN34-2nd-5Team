function formatPercent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

const columns = "grid-cols-[56px_170px_110px_110px_100px_130px_1fr]";

function RegionalRiskTable({ regions, minimumReviewers, hoveredRegion, onHoverRegion }) {
  if (regions.length === 0) {
    return (
      <div className="rounded-xl bg-[#F1F4F1] px-6 py-12 text-center">
        <h2 className="font-bold text-[#17211D]">
          표시할 권역이 없습니다
        </h2>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-[#DDE4DF] bg-white">
      <div className="min-w-[1000px]">
        <div
          className={`grid ${columns} gap-3 border-b border-[#DDE4DF] px-5 py-3 text-xs font-semibold text-[#626D67]`}
        >
          <span>순위</span>
          <span>권역</span>
          <span>활동 리뷰어</span>
          <span>고위험 리뷰어</span>
          <span>고위험 비율</span>
          <span>통합 검토 대상</span>
          <span>구성</span>
        </div>

        {regions.map((region, index) => (
          <div
            key={region.region}
            onMouseEnter={() => onHoverRegion?.(region.region)}
            onMouseLeave={() => onHoverRegion?.(null)}
            className={[
              `grid ${columns} items-center gap-3 border-b border-[#DDE4DF] px-5 py-2.5 text-sm last:border-b-0`,
              hoveredRegion === region.region ? "bg-[#E3F1EA]" : "hover:bg-[#F6F8F6]",
            ].join(" ")}
          >
            <span className="font-bold text-[#17211D]">{index + 1}</span>

            <div>
              <strong className="text-[#17211D]">{region.region}</strong>

              <p className="mt-1 text-xs text-[#626D67]">
                {region.topCity} 중심
              </p>
            </div>

            <span className="text-[#626D67]">
              {region.reviewers.toLocaleString()}명
              {region.belowMinimum && (
                <span className="ml-1 rounded bg-[#FAEFD9] px-1 py-0.5 text-[10px] font-bold text-[#A66A18]">
                  표본 {minimumReviewers}명 미만
                </span>
              )}
            </span>

            <span className="font-bold text-[#17211D]">
              {region.highRisk.toLocaleString()}명
            </span>

            <span className="font-bold text-[#BF3620]">
              {formatPercent(region.highRiskRate)}
            </span>

            <span className="text-[#626D67]">
              {region.crmTargets.toLocaleString()}명
            </span>

            <span className="text-xs text-[#626D67]">
              유지 {region.retained.toLocaleString()} · 약화{" "}
              {region.weakened.toLocaleString()} · 중단{" "}
              {region.stopped.toLocaleString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default RegionalRiskTable;
