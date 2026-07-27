const fieldClassName =
  "min-h-11 rounded-lg border border-[#DDE4DF] bg-white px-3 text-sm text-[#17211D] outline-none transition focus:border-[#137A5A]";

function ReviewerFilters({
  searchText,
  onSearchChange,
  statusFilter,
  onStatusChange,
  judgmentFilter,
  onJudgmentChange,
  riskTypeFilter,
  onRiskTypeChange,
  sortRule,
  onSortChange,
  riskTypes,
}) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-4">
      <div className="grid gap-3 lg:grid-cols-[1.6fr_repeat(4,1fr)]">
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
          value={judgmentFilter}
          onChange={(event) => onJudgmentChange(event.target.value)}
          className={fieldClassName}
        >
          <option value="전체">모델 판단 전체</option>
          <option value="유지 우세">유지 우세</option>
          <option value="약화 우세">약화 우세</option>
          <option value="중단 우세">중단 우세</option>
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
          value={sortRule}
          onChange={(event) => onSortChange(event.target.value)}
          className={fieldClassName}
        >
          <option value="우선순위">통합 우선순위</option>
          <option value="리뷰 공백">리뷰 공백순</option>
          <option value="최근 활동 월">최근 활동 월 적은 순</option>
        </select>
      </div>
    </div>
  );
}

export default ReviewerFilters;