function formatPercent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

const columns = "grid-cols-[56px_170px_110px_110px_100px_130px_1fr]";

function RegionalRiskTable({ regions, minimumReviewers }) {
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
          className={`grid ${columns} gap-3 border-b border-[#DDE4DF] px-5 py-3 text-xs font-semibold text-[#68736D]`}
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
            className={`grid ${columns} items-center gap-3 border-b border-[#DDE4DF] px-5 py-4 text-sm last:border-b-0 hover:bg-[#F6F8F6]`}
          >
            <span className="font-bold text-[#17211D]">{index + 1}</span>

            <div>
              <strong className="text-[#17211D]">{region.region}</strong>

              <p className="mt-1 text-xs text-[#68736D]">
                {region.topCity} 중심
              </p>
            </div>

            <span className="text-[#68736D]">
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

            <span className="font-bold text-[#E15D47]">
              {formatPercent(region.highRiskRate)}
            </span>

            <span className="text-[#68736D]">
              {region.crmTargets.toLocaleString()}명
            </span>

            <span className="text-xs text-[#68736D]">
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
