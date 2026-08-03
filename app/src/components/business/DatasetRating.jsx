function formatReviewCount(reviewCount) {
  if (!Number.isFinite(reviewCount)) return null;
  return reviewCount.toLocaleString();
}

function DatasetRating({ stars, reviewCount, compact = false, showSource = false }) {
  const rating = Number.isFinite(stars) ? Math.min(5, Math.max(0, stars)) : 0;
  const formattedCount = formatReviewCount(reviewCount);

  return (
    <div className={`flex flex-wrap items-center ${compact ? "gap-1" : "gap-1.5"}`} aria-label={`데이터셋 평점 ${rating.toFixed(1)}점${formattedCount ? `, 리뷰 ${formattedCount}건` : ""}`}>
      <span className="inline-flex gap-0.5" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((index) => {
          const fill = Math.min(1, Math.max(0, rating - index)) * 100;
          return (
            <span
              key={index}
                className={`grid place-items-center rounded-[3px] border border-white/35 font-black leading-none text-white shadow-[0_1px_1px_rgba(23,33,29,0.12)] ${compact ? "h-4 w-4 text-[10px]" : "h-[18px] w-[18px] text-xs"}`}
              style={{ background: `linear-gradient(90deg, #FF643D ${fill}%, #D6D9D7 ${fill}%)` }}
            >
              ★
            </span>
          );
        })}
      </span>
      <strong className={`${compact ? "text-[11px]" : "text-xs"} text-[#17211D]`}>{rating.toFixed(1)}</strong>
      {formattedCount && <span className={`${compact ? "text-[10px]" : "text-[11px]"} text-[#718078]`}>리뷰 {formattedCount}건</span>}
      {showSource && <span className="text-[9px] text-[#8A948F]">데이터셋 수집 시점</span>}
    </div>
  );
}

export default DatasetRating;
