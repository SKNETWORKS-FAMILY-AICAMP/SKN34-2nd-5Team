import { Link } from "react-router";

function RegionalInsightPanel({ region }) {
  if (!region) {
    return <aside className="rounded-2xl border border-dashed border-[#B7CFC2] bg-[#F8FBF9] p-6 text-sm leading-6 text-[#626D67]">지도에서 권역 핀을 선택하면 공급 변화, 고위험 리뷰어, CRM 대상과 다음 작업을 함께 확인할 수 있습니다.</aside>;
  }
  const change = region.reviewSupplyChangeRate;
  const changeLabel = change === null || change === undefined
    ? "전년 비교 불가"
    : change < 0
      ? "실제 공급 감소"
      : "상대 둔화 검토";
  return (
    <aside className="overflow-hidden rounded-2xl border border-[#B7D8C8] bg-white">
      <div className="bg-[#075C45] px-6 py-5 text-white">
        <div className="flex items-center justify-between gap-3"><p className="text-[10px] font-black tracking-[0.14em] text-[#BDE2CF]">SELECTED REGION</p><span className={`rounded-full px-2.5 py-1 text-[10px] font-black ${change < 0 ? "bg-[#FFE6E1] text-[#B93D29]" : "bg-white/12 text-white"}`}>{changeLabel}</span></div>
        <h2 className="mt-2 text-2xl font-black">{region.region} · {region.topCity}</h2>
        <p className="mt-2 text-xs leading-5 text-white/65">대표 활동 도시는 지도 설명용 보조 정보이며 거주지나 생활권을 의미하지 않습니다.</p>
      </div>
      <div className="p-5">
        <dl className="grid grid-cols-2 gap-3">
          <Metric label="리뷰 공급 변화" value={change === null || change === undefined ? "비교 불가" : `${change >= 0 ? "+" : ""}${(change * 100).toFixed(1)}%`} emphasis={change < 0} />
          <Metric label="고위험 비율" value={`${(region.highRiskRate * 100).toFixed(1)}%`} />
          <Metric label="CRM 검토 대상" value={`${region.crmTargets.toLocaleString()}명`} />
          <Metric label="신규 핵심 리뷰어" value={`${(region.newPowerReviewers ?? 0).toLocaleString()}명`} />
        </dl>

        <div className="mt-5 rounded-xl bg-[#F0F7F3] p-4">
          <p className="text-xs font-black text-[#075C45]">다음 작업</p>
          <p className="mt-2 text-xs leading-5 text-[#4B665B]">CRM 후보의 활동 근거와 관리자 판단 상태를 확인한 뒤 캠페인 대상 조건을 결정합니다.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="rounded-full bg-white px-2.5 py-1 text-[10px] font-bold text-[#4B665B]">대상 {region.crmTargets.toLocaleString()}명</span>
            <span className="rounded-full bg-white px-2.5 py-1 text-[10px] font-bold text-[#4B665B]">위험 신호별 검토</span>
          </div>
        </div>

        <Link to={`/reviewers?region=${encodeURIComponent(region.region)}`} className="mt-5 flex min-h-12 items-center justify-center rounded-xl bg-[#075C45] px-4 text-sm font-black text-white hover:bg-[#064936]">이 권역 대상 검토하기 →</Link>
      </div>
    </aside>
  );
}

function Metric({ label, value, emphasis }) { return <div className="rounded-xl border border-[#E2E7E3] bg-[#FAFBFA] p-3"><dt className="text-[11px] text-[#718078]">{label}</dt><dd className={`mt-1 text-lg font-black ${emphasis ? "text-[#C94734]" : "text-[#17211D]"}`}>{value}</dd></div>; }

export default RegionalInsightPanel;
