const fieldClassName =
  "min-h-11 rounded-lg border border-[#DDE4DF] bg-white px-3 text-sm text-[#17211D] outline-none transition focus:border-[#137A5A]";

function PlaybookFilters({
  judgmentFilter,
  onJudgmentChange,
  riskTypeFilter,
  onRiskTypeChange,
  riskTypes,
}) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-4">
      <div className="grid gap-3 md:grid-cols-2">
        <select
          value={judgmentFilter}
          onChange={(event) =>
            onJudgmentChange(event.target.value)
          }
          className={fieldClassName}
        >
          <option value="전체">모델 판단 전체</option>
          <option value="유지 우세">유지 우세</option>
          <option value="약화 우세">약화 우세</option>
          <option value="중단 우세">중단 우세</option>
        </select>

        <select
          value={riskTypeFilter}
          onChange={(event) =>
            onRiskTypeChange(event.target.value)
          }
          className={fieldClassName}
        >
          <option value="전체">위험 유형 전체</option>

          {riskTypes.map((riskType) => (
            <option key={riskType} value={riskType}>
              {riskType}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

export default PlaybookFilters;