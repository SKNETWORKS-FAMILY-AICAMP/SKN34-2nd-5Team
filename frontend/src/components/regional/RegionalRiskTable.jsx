function formatPercent(value) {
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function getRiskStyle(riskLevel) {
  if (riskLevel === "매우 높음") {
    return "bg-[#F7E8E5] text-[#E15D47]";
  }

  if (riskLevel === "높음") {
    return "bg-[#FAEFD9] text-[#A66A18]";
  }

  if (riskLevel === "보통") {
    return "bg-[#E6EFF1] text-[#356A78]";
  }

  return "bg-[#E3F1EA] text-[#137A5A]";
}

function RegionalRiskTable({ regions }) {
  if (regions.length === 0) {
    return (
      <div className="rounded-xl bg-[#F1F4F1] px-6 py-12 text-center">
        <h2 className="font-bold text-[#17211D]">
          조건에 해당하는 지역이 없습니다
        </h2>

        <p className="mt-2 text-sm text-[#68736D]">
          검색어나 필터 조건을 변경해 주세요.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-[#DDE4DF] bg-white">
      <div className="min-w-[1100px]">
        <div className="grid grid-cols-[60px_150px_80px_120px_120px_110px_110px_1fr] gap-3 border-b border-[#DDE4DF] px-5 py-3 text-xs font-semibold text-[#68736D]">
          <span>순위</span>
          <span>지역</span>
          <span>등급</span>
          <span>전체 리뷰어</span>
          <span>약화·중단</span>
          <span>위험률</span>
          <span>평균 감소율</span>
          <span>주요 신호</span>
        </div>

        {regions.map((region, index) => {
          const riskReviewerCount =
            region.weakened + region.stopped;

          return (
            <div
              key={`${region.state}-${region.city}`}
              className="grid grid-cols-[60px_150px_80px_120px_120px_110px_110px_1fr] items-center gap-3 border-b border-[#DDE4DF] px-5 py-4 text-sm last:border-b-0 hover:bg-[#F6F8F6]"
            >
              <span className="font-bold text-[#17211D]">
                {index + 1}
              </span>

              <div>
                <strong className="text-[#17211D]">
                  {region.city}
                </strong>

                <p className="mt-1 text-xs text-[#68736D]">
                  {region.state}
                </p>
              </div>

              <span
                className={[
                  "w-fit rounded px-2 py-1 text-xs font-bold",
                  getRiskStyle(region.riskLevel),
                ].join(" ")}
              >
                {region.riskLevel}
              </span>

              <span className="text-[#68736D]">
                {region.totalReviewers.toLocaleString()}명
              </span>

              <span className="font-bold text-[#17211D]">
                {riskReviewerCount.toLocaleString()}명
              </span>

              <span className="font-bold text-[#E15D47]">
                {formatPercent(region.riskRate)}
              </span>

              <span className="text-[#68736D]">
                {formatPercent(
                  region.averageReviewDecline,
                )}
              </span>

              <span className="text-[#68736D]">
                {region.mainSignal}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default RegionalRiskTable;