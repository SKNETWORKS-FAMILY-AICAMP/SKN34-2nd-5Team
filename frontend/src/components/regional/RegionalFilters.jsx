const fieldClassName =
  "min-h-11 rounded-lg border border-[#DDE4DF] bg-white px-3 text-sm text-[#17211D] outline-none transition focus:border-[#137A5A]";

function RegionalFilters({
  searchText,
  onSearchChange,
  stateFilter,
  onStateChange,
  riskLevelFilter,
  onRiskLevelChange,
  sortRule,
  onSortChange,
  states,
  riskLevels,
}) {
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white p-4">
      <div className="grid gap-3 lg:grid-cols-[1.4fr_repeat(3,1fr)]">
        <input
          type="search"
          value={searchText}
          onChange={(event) =>
            onSearchChange(event.target.value)
          }
          placeholder="도시 검색"
          className={fieldClassName}
        />

        <select
          value={stateFilter}
          onChange={(event) =>
            onStateChange(event.target.value)
          }
          className={fieldClassName}
        >
          <option value="전체">주 전체</option>

          {states.map((state) => (
            <option key={state} value={state}>
              {state}
            </option>
          ))}
        </select>

        <select
          value={riskLevelFilter}
          onChange={(event) =>
            onRiskLevelChange(event.target.value)
          }
          className={fieldClassName}
        >
          <option value="전체">위험 등급 전체</option>

          {riskLevels.map((riskLevel) => (
            <option key={riskLevel} value={riskLevel}>
              {riskLevel}
            </option>
          ))}
        </select>

        <select
          value={sortRule}
          onChange={(event) =>
            onSortChange(event.target.value)
          }
          className={fieldClassName}
        >
          <option value="우선순위">
            콘텐츠 위험 우선순위
          </option>

          <option value="위험률">
            위험률 높은 순
          </option>

          <option value="위험 리뷰어">
            약화·중단 리뷰어 많은 순
          </option>

          <option value="전체 리뷰어">
            전체 리뷰어 많은 순
          </option>
        </select>
      </div>
    </div>
  );
}

export default RegionalFilters;