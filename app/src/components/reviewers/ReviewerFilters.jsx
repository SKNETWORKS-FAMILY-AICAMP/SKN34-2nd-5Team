const fieldClassName = "min-h-9 rounded-lg border border-[#DDE4DF] bg-white px-2.5 text-[11px] font-bold text-[#26312C] outline-none transition focus:border-[#137A5A] focus-visible:ring-2 focus-visible:ring-[#137A5A]/20";

function ReviewerFilters({
  searchText, onSearchChange,
  scopeFilter, onScopeChange,
  regionFilter, onRegionChange, regionOptions,
  cityFilter, onCityChange, cityOptions,
  statusFilter, onStatusChange,
  riskTypeFilter, onRiskTypeChange,
  sortRule, onSortChange, riskTypes,
  modelJudgmentFilter, onModelJudgmentChange,
  crmRangeFilter, onCrmRangeChange,
  recencyFilter, onRecencyChange,
  activeMonthsFilter, onActiveMonthsChange,
  pendingCount, completedCount, totalCount,
}) {
  const progress = totalCount > 0 ? completedCount / totalCount : 0;
  return (
    <div className="rounded-xl border border-[#DDE4DF] bg-white px-3 py-2.5 shadow-[0_2px_8px_rgba(23,33,29,0.03)]">
      <div className="flex flex-wrap items-center gap-2">
        <label className="relative min-w-[210px] flex-1 lg:max-w-[270px]">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[#718078]">⌕</span>
          <input type="search" aria-label="리뷰어 ID 검색" value={searchText} onChange={(event) => onSearchChange(event.target.value)} placeholder="리뷰어 ID 검색" className={`${fieldClassName} w-full pl-8 pr-10`} />
          <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded bg-[#F1F4F1] px-1.5 py-0.5 text-[9px] font-medium text-[#718078]">Ctrl K</kbd>
        </label>

        <select value={scopeFilter} onChange={(event) => onScopeChange(event.target.value)} className={`${fieldClassName} min-w-[126px]`} aria-label="검토 범위">
          <option value="region">권역 종합</option><option value="core">핵심 리뷰어</option><option value="newcomers">신규 유입</option>
        </select>
        <select value={regionFilter} onChange={(event) => onRegionChange(event.target.value)} className={`${fieldClassName} min-w-[92px]`} aria-label="권역">
          <option value="전체">권역 전체</option>{regionOptions.map((region) => <option key={region} value={region}>{region}</option>)}
        </select>
        <select value={cityFilter} onChange={(event) => onCityChange(event.target.value)} className={`${fieldClassName} min-w-[128px]`} aria-label="도시">
          <option value="전체">도시 전체</option>{cityOptions.map((city) => <option key={city} value={city}>{city}</option>)}
        </select>

        <button type="button" onClick={() => onStatusChange("미검토")} className={`min-h-9 rounded-lg px-2.5 text-[11px] font-bold ${statusFilter === "미검토" ? "bg-[#EAF4EF] text-[#075C45]" : "text-[#626D67] hover:bg-[#F4F7F5]"}`}>미검토 <strong className="ml-1 rounded bg-[#075C45] px-1.5 py-0.5 text-white">{pendingCount.toLocaleString()}</strong></button>
        <button type="button" onClick={() => onStatusChange("검토 완료")} className={`min-h-9 rounded-lg px-2.5 text-[11px] font-bold ${statusFilter === "검토 완료" ? "bg-[#EAF4EF] text-[#075C45]" : "text-[#626D67] hover:bg-[#F4F7F5]"}`}>완료 <strong className="ml-1 rounded bg-[#EEF1EF] px-1.5 py-0.5 text-[#26312C]">{completedCount.toLocaleString()}</strong></button>
        <button type="button" onClick={() => onStatusChange("전체")} className={`min-h-9 px-1.5 text-[10px] font-bold ${statusFilter === "전체" ? "text-[#075C45] underline" : "text-[#718078]"}`}>전체</button>

        <select value={riskTypeFilter} onChange={(event) => onRiskTypeChange(event.target.value)} className={`${fieldClassName} min-w-[125px]`}><option value="전체">위험 유형 전체</option>{riskTypes.map((riskType) => <option key={riskType} value={riskType}>{riskType}</option>)}</select>
        <select value={sortRule} onChange={(event) => onSortChange(event.target.value)} className={`${fieldClassName} min-w-[126px]`}><option value="우선순위">우선순위 높은 순</option><option value="중단 점수">중단 점수 높은 순</option><option value="약화 점수">약화 점수 높은 순</option><option value="활동 감소순">활동 감소순</option><option value="리뷰 공백">리뷰 공백순</option></select>

        <div className="ml-auto flex min-w-[190px] items-center gap-2 px-1"><strong className="whitespace-nowrap text-[11px] text-[#17211D]">{totalCount.toLocaleString()}명 중 {completedCount.toLocaleString()}명</strong><div className="h-1.5 min-w-12 flex-1 rounded-full bg-[#E8ECE9]"><div className="h-1.5 rounded-full bg-[#137A5A]" style={{ width: `${Math.min(100, progress * 100)}%` }} /></div><span className="text-[10px] font-black text-[#137A5A]">{(progress * 100).toFixed(1)}%</span></div>
      </div>

      <details className="mt-2 border-t border-[#EEF1EF] pt-2">
        <summary className="w-fit cursor-pointer text-[10px] font-bold text-[#526159] hover:text-[#075C45]">상세 필터</summary>
        <div className="mt-2 flex flex-wrap gap-2">
          <select value={modelJudgmentFilter} onChange={(event) => onModelJudgmentChange(event.target.value)} className={fieldClassName}><option value="전체">모델 판단 전체</option><option value="유지 우세">유지 우세</option><option value="약화 우세">약화 우세</option><option value="중단 우세">중단 우세</option></select>
          <select value={crmRangeFilter} onChange={(event) => onCrmRangeChange(event.target.value)} className={fieldClassName}><option value="전체">통합 검토 범위 전체</option><option value="상위 20%">통합 상위 20%</option><option value="상위 20% 제외">상위 20% 제외</option></select>
          <select value={recencyFilter} onChange={(event) => onRecencyChange(event.target.value)} className={fieldClassName}><option value="전체">리뷰 공백 전체</option><option value="0-45">0–45일</option><option value="45-90">45–90일</option><option value="90-180">90–180일</option><option value="180+">180일 이상</option></select>
          <select value={activeMonthsFilter} onChange={(event) => onActiveMonthsChange(event.target.value)} className={fieldClassName}><option value="전체">활동 월 전체</option>{Array.from({ length: 12 }, (_, index) => index + 1).map((month) => <option key={month} value={String(month)}>{month}개월</option>)}</select>
        </div>
      </details>
    </div>
  );
}

export default ReviewerFilters;
