import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";

import { loadDecisionHistory } from "../../services/decisionService";

function operatingGrade(percent) {
  if (!Number.isFinite(percent)) return { label: "산정 불가", note: "순위 자료 없음", tone: "text-[#626D67]" };
  if (percent <= 2) return { label: "높음", note: `상위 ${Math.max(0.1, percent).toFixed(1)}%`, tone: "text-[#E64A35]" };
  if (percent <= 10) return { label: "중간", note: `상위 ${percent.toFixed(1)}%`, tone: "text-[#A66A18]" };
  return { label: "관찰", note: `상위 ${percent.toFixed(1)}%`, tone: "text-[#137A5A]" };
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("ko-KR", { year: "2-digit", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
}

function ReviewerSplitPanel({ reviewer, scope = "core", detailHref }) {
  const [history, setHistory] = useState([]);
  const [historyState, setHistoryState] = useState("loading");
  const grade = useMemo(() => operatingGrade(reviewer.priorityTopPercent), [reviewer.priorityTopPercent]);
  const evidence = Array.isArray(reviewer.metrics) ? reviewer.metrics : [];
  const signalRows = scope === "newcomers"
    ? [
        { glyph: "★", label: "최초 코호트 진입", value: reviewer.firstPowerYear ? `${reviewer.firstPowerYear}년` : "—", note: reviewer.topCity ? `${reviewer.region} · ${reviewer.topCity}` : "활동 도시 확인 불가" },
        { glyph: "▣", label: "선정 연도 활동", value: `${reviewer.recentActiveMonths ?? 0}개월`, note: "2018년 공개 음식점 리뷰 활동" },
        { glyph: "○", label: "최근 리뷰 공백", value: `${Math.round(reviewer.recentRecencyDays ?? 0)}일`, note: "2018년 마지막 공개 리뷰 기준" },
      ]
    : [
        { glyph: "↘", label: "핵심 변화 근거", value: evidence[0] || reviewer.coreSignal || "변화 관찰", note: reviewer.priorActivityAvailable ? "2017년 대비 2018년 비교" : "2017년 비교 활동 없음" },
        { glyph: "▣", label: "보조 변화 근거", value: evidence[1] || `${reviewer.recentActiveMonths ?? 0}개월 활동`, note: "공개 음식점 리뷰 활동 기준" },
        { glyph: "○", label: "최근 리뷰 공백", value: `${Math.round(reviewer.recentRecencyDays ?? 0)}일`, note: "2018년 마지막 공개 리뷰 기준" },
      ];

  useEffect(() => {
    let active = true;
    Promise.allSettled([loadDecisionHistory(reviewer.userId)]).then(([historyResult]) => {
      if (!active) return;
      if (historyResult.status === "fulfilled") {
        setHistory(historyResult.value?.items ?? []);
        setHistoryState("ready");
      } else {
        setHistory([]);
        setHistoryState("error");
      }
    });
    return () => { active = false; };
  }, [reviewer.userId]);

  return (
    <aside className="overflow-hidden rounded-xl border border-[#D3DED7] bg-white shadow-[0_10px_28px_rgba(23,33,29,0.06)]">
      <header className="border-b border-[#E3E8E5] px-4 py-4">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-black text-[#17211D]">선택한 리뷰어</h2>
          <span className={`rounded-md border px-2 py-0.5 text-[10px] font-bold ${reviewer.managerDecision ? "border-[#B7D8C8] bg-[#EAF4EF] text-[#075C45]" : "border-[#FF8C7A] bg-[#FFF5F2] text-[#E64A35]"}`}>{reviewer.managerDecision ? "검토 완료" : "미검토"}</span>
        </div>
        <p className="mt-3 break-all text-base font-black text-[#17211D]">{reviewer.userId}</p>
        <p className="mt-1 text-[10px] text-[#718078]">{reviewer.region ? `${reviewer.region} · ${reviewer.topCity ?? "활동 도시 확인 불가"}` : "활동 권역 확인 불가"}{reviewer.isNewcomer ? " · 신규 유입" : ""}</p>
        <div className="mt-3 grid grid-cols-3 divide-x divide-[#E3E8E5]">
          <Metric label="우선순위" value={`${reviewer.priorityRank}위`} accent />
          <Metric label="위험 유형" value={reviewer.riskType} />
          <Metric label="상태" value={reviewer.managerDecision ? "판단 완료" : "미검토"} />
        </div>
      </header>

      <section className="border-b border-[#E3E8E5] px-4 py-4">
        <h3 className="text-xs font-black text-[#17211D]">관찰 신호</h3>
        <div className="mt-2 divide-y divide-[#EEF2EF] rounded-lg border border-[#E3E8E5]">
          {signalRows.map((signal) => <div key={signal.label} className="grid min-h-12 grid-cols-[22px_1fr] items-start gap-2 px-3 py-2.5"><span className="pt-0.5 text-sm font-black text-[#137A5A]">{signal.glyph}</span><span className="min-w-0"><span className="flex items-start justify-between gap-3"><strong className="shrink-0 text-[11px] text-[#26312C]">{signal.label}</strong>{signal.label === "최근 리뷰 공백" || scope === "newcomers" ? <strong className="text-right text-xs text-[#075C45]">{signal.value}</strong> : null}</span>{signal.label !== "최근 리뷰 공백" && scope !== "newcomers" && <strong className="mt-1 block text-[11px] leading-4 text-[#075C45]">{signal.value}</strong>}<small className="mt-1 block text-[9px] text-[#718078]">{signal.note}</small></span></div>)}
        </div>
      </section>

      <section className="border-b border-[#E3E8E5] px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-xs font-black text-[#17211D]">모델 판단 · 운영 등급</h3>
            <p className="mt-1 text-[10px] leading-4 text-[#718078]">모델 점수는 확률이 아닌 검토 우선순위 지표입니다.</p>
          </div>
          <div className="text-right">
            <strong className={`block text-sm font-black ${grade.tone}`}>{reviewer.modelJudgment || grade.label}</strong>
            <span className="text-[10px] text-[#718078]">{grade.note}</span>
          </div>
        </div>
        <div className="mt-3 rounded-lg border border-[#E3E8E5] bg-[#F8FAF8] px-3 py-2 text-[11px] text-[#4F5D56]">
          <strong className="text-[#26312C]">산출 기준</strong><span className="ml-2">리뷰 활동 변화, 최근 공백, 활동 충성도 및 통합 우선순위</span>
        </div>
      </section>

      <section className="px-4 py-4">
        <h3 className="text-xs font-black text-[#17211D]">관리자 판단 이력</h3>
        {historyState === "loading" ? (
          <p className="mt-2 text-[11px] text-[#718078]">이력을 불러오는 중입니다.</p>
        ) : history.length === 0 ? (
          <div className="mt-2 rounded-lg bg-[#F8FAF8] px-3 py-3 text-[11px] leading-5 text-[#626D67]">아직 관리자 판단이 없습니다.<br />Reviewer 360에서 상세 근거를 검토한 후 판단을 남겨주세요.</div>
        ) : (
          <div className="mt-2 overflow-hidden rounded-lg border border-[#E3E8E5]">
            {history.slice(0, 3).map((item) => (
              <div key={item.historyId} className="grid grid-cols-[82px_1fr] gap-2 border-b border-[#EEF2EF] px-3 py-2 text-[10px] last:border-b-0">
                <span className="text-[#718078]">{formatDate(item.changedAt)}</span>
                <span className="min-w-0"><strong className="block truncate text-[#26312C]">{item.toDecision ?? "판단 취소"}</strong><span className="text-[#718078]">{item.actor?.name || item.actor?.subject || "관리자"}</span></span>
              </div>
            ))}
          </div>
        )}
        {historyState === "error" && <p className="mt-2 text-[10px] text-[#B46A20]">판단 이력을 불러오지 못했습니다. Reviewer 360에서 다시 확인하세요.</p>}

        <Link to={detailHref ?? `/reviewers/${encodeURIComponent(reviewer.userId)}`} className="mt-4 flex min-h-12 items-center justify-center rounded-xl bg-[#075C45] px-4 text-sm font-black text-white transition hover:bg-[#064D3B]">
          Reviewer 360에서 검토 <span className="ml-3 text-lg">→</span>
        </Link>
      </section>
    </aside>
  );
}

function Metric({ label, value, accent = false }) {
  return <div className="min-w-0 px-3 first:pl-0 last:pr-0"><span className="block text-[10px] text-[#718078]">{label}</span><strong className={`mt-1 block truncate text-sm ${accent ? "text-[#E64A35]" : "text-[#26312C]"}`} title={value}>{value}</strong></div>;
}

export default ReviewerSplitPanel;
