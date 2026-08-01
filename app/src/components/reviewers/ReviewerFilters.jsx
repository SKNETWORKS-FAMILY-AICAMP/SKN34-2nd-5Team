const fieldClassName =
  "min-h-11 rounded-lg border border-[#DDE4DF] bg-white px-3 text-sm text-[#17211D] outline-none transition focus:border-[#137A5A]";

const judgmentOptions = ["유지 우세", "약화 우세", "중단 우세"];

function ReviewerFilters({
  searchText,
  onSearchChange,
  statusFilter,
  onStatusChange,
  judgmentFilters,
  onJudgmentFiltersChange,
  riskTypeFilter,
  onRiskTypeChange,
  crmRangeFilter,
  onCrmRangeChange,
  sortRule,
  onSortChange,
  riskTypes,
}) {
  function toggleJudgment(option) {
    if (judgmentFilters.includes(option)) {
      onJudgmentFiltersChange(
        judgmentFilters.filter((item) => item !== option),
      );
    } else {
      onJudgmentFiltersChange([...judgmentFilters, option]);
    }
  }

  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-4">
      <div className="grid gap-3 lg:grid-cols-[1.4fr_repeat(4,1fr)]">
        <input
          type="search"
          value={searchText}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="리뷰어 ID 검색"
          className={fieldClassName}
        />

        <select
          value={statusFilter}
          onChange={(event) => onStatusChange(event.target.value)}
          className={fieldClassName}
        >
          <option value="전체">검토 상태 전체</option>
          <option value="미검토">미검토</option>
          <option value="검토 완료">검토 완료</option>
        </select>

        <select
          value={riskTypeFilter}
          onChange={(event) => onRiskTypeChange(event.target.value)}
          className={fieldClassName}
        >
          <option value="전체">위험 유형 전체</option>

          {riskTypes.map((riskType) => (
            <option key={riskType} value={riskType}>
              {riskType}
            </option>
          ))}
        </select>

        <select
          value={crmRangeFilter}
          onChange={(event) => onCrmRangeChange(event.target.value)}
          className={fieldClassName}
          title="통합 검토 범위: 중단·약화 점수를 합친 통합 우선순위 기준 상위 20% 여부입니다. 개별 확률이 아닙니다."
        >
          <option value="전체">통합 검토 범위 전체</option>
          <option value="상위 20%">통합 상위 20%</option>
          <option value="상위 20% 제외">상위 20% 제외</option>
        </select>

        <select
          value={sortRule}
          onChange={(event) => onSortChange(event.target.value)}
          className={fieldClassName}
          title="통합 우선순위: 중단·약화 점수를 합친 통합 점수로 정렬합니다. 보정된 이탈 확률이 아닙니다."
        >
          <option value="우선순위">통합 우선순위</option>
          <option value="중단 점수">중단 점수 높은 순</option>
          <option value="약화 점수">약화 점수 높은 순</option>
          <option value="활동 감소순">활동 감소순</option>
          <option value="리뷰 공백">리뷰 공백순</option>
        </select>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-[#626D67]">
          모델 판단
        </span>

        {judgmentOptions.map((option) => {
          const isActive = judgmentFilters.includes(option);

          return (
            <button
              key={option}
              type="button"
              onClick={() => toggleJudgment(option)}
              className={[
                "rounded-full border px-3 py-1 text-xs font-bold transition",
                isActive
                  ? "border-[#137A5A] bg-[#E3F1EA] text-[#137A5A]"
                  : "border-[#DDE4DF] text-[#626D67] hover:border-[#137A5A]",
              ].join(" ")}
            >
              {option}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default ReviewerFilters;
