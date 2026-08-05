import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";

import ErrorState from "../components/common/ErrorState";
import Skeleton from "../components/common/Skeleton";
import GlobalWorkflowStepper from "../components/workflow/GlobalWorkflowStepper";
import { useReviewers } from "../context/operations-context";
import {
  loadOperationsHistory,
  loadReviewAlertHistory,
  resolveReviewAlert,
} from "../services/operationsHistoryService";

const tabs = [
  ["due", "재검토 알림"],
  ["plans", "운영안"],
  ["lists", "대상 명단"],
  ["decisions", "판단·감사 이력"],
  ["contacts", "접촉 이력"],
];

const formatter = new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" });

const workflowSteps = [
  { label: "운영 신호 확인", href: "/" },
  { label: "대상 선정", href: "/reviewers?mode=individual&status=미검토&sort=우선순위" },
  { label: "근거 검토·판단" },
  { label: "운영안 설계", href: "/playbook" },
  { label: "실행·성과 추적" },
];

function formatDate(value) {
  if (!value) return "-";
  return formatter.format(new Date(value));
}

function dayKey(value = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(value));
  const part = (type) => parts.find((item) => item.type === type)?.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}

function alertTiming(alert) {
  if (alert.status === "completed") return { key: "completed", label: "처리 완료", tone: "green" };
  if (alert.status === "dismissed") return { key: "dismissed", label: "제외", tone: "gray" };
  const due = dayKey(alert.dueAt);
  const today = dayKey();
  if (due < today) return { key: "overdue", label: "기한 경과", tone: "red" };
  if (due === today) return { key: "today", label: "오늘 마감", tone: "orange" };
  return { key: "upcoming", label: "예정", tone: "gray" };
}

function OperationsHistoryPage() {
  const reviewers = useReviewers();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedTab = searchParams.get("tab");
  const highlightedPlanId = searchParams.get("planId");
  const [selectedTab, setSelectedTab] = useState("due");
  const active = tabs.some(([key]) => key === requestedTab) ? requestedTab : selectedTab;
  const [state, setState] = useState({ status: "loading", data: null, error: null });
  const [selectedAlertId, setSelectedAlertId] = useState(null);
  const [selectedPlanId, setSelectedPlanId] = useState(highlightedPlanId ? Number(highlightedPlanId) : null);
  const [selectedListId, setSelectedListId] = useState(null);
  const [alertHistory, setAlertHistory] = useState([]);
  const [resolutionNote, setResolutionNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [regionFilter, setRegionFilter] = useState("전체");
  const [assigneeFilter, setAssigneeFilter] = useState("전체");
  const [statusFilter, setStatusFilter] = useState("전체");
  const [typeFilter, setTypeFilter] = useState("전체");

  useEffect(() => {
    loadOperationsHistory()
      .then((data) => setState({ status: "ready", data, error: null }))
      .catch((error) => setState({ status: "error", data: null, error }));
  }, []);

  const data = state.data;
  const reviewerById = useMemo(() => new Map(reviewers.map((reviewer) => [reviewer.userId, reviewer])), [reviewers]);
  const alerts = useMemo(() => data?.reviewAlerts ?? [], [data]);
  const regions = useMemo(() => [...new Set(alerts.map((item) => item.region).filter(Boolean))].sort(), [alerts]);
  const assignees = useMemo(() => {
    const values = new Map();
    alerts.forEach((item) => {
      if (item.assignedTo?.subject) values.set(item.assignedTo.subject, item.assignedTo.name || item.assignedTo.subject);
    });
    return [...values.entries()];
  }, [alerts]);
  const riskTypes = useMemo(() => [...new Set(alerts.map((item) => item.riskType).filter(Boolean))].sort(), [alerts]);

  const filteredAlerts = useMemo(() => alerts.filter((alert) => {
    const timing = alertTiming(alert);
    if (regionFilter !== "전체" && alert.region !== regionFilter) return false;
    if (assigneeFilter !== "전체" && alert.assignedTo?.subject !== assigneeFilter) return false;
    if (statusFilter !== "전체" && timing.key !== statusFilter) return false;
    if (typeFilter !== "전체" && alert.riskType !== typeFilter) return false;
    return true;
  }), [alerts, assigneeFilter, regionFilter, statusFilter, typeFilter]);

  const selectedAlert = filteredAlerts.find((item) => item.alertId === selectedAlertId) ?? filteredAlerts[0] ?? null;
  useEffect(() => {
    if (!selectedAlert) return undefined;
    let activeRequest = true;
    loadReviewAlertHistory(selectedAlert.alertId)
      .then(({ items }) => {
        if (activeRequest) setAlertHistory(items ?? []);
      })
      .catch(() => {
        if (activeRequest) setAlertHistory([]);
      });
    return () => {
      activeRequest = false;
    };
  }, [selectedAlert]);

  const rows = useMemo(() => {
    if (!data) return [];
    if (active === "lists") return data.targetLists;
    if (active === "decisions") return data.decisionHistory;
    if (active === "contacts") return data.interactions;
    if (active === "plans") return data.actionPlans;
    return filteredAlerts;
  }, [active, data, filteredAlerts]);

  const todayCount = alerts.filter((item) => alertTiming(item).key === "today").length;
  const overdueCount = alerts.filter((item) => alertTiming(item).key === "overdue").length;
  const selectedPlan = data?.actionPlans?.find((item) => item.planId === selectedPlanId)
    ?? data?.actionPlans?.find((item) => String(item.planId) === highlightedPlanId)
    ?? data?.actionPlans?.[0]
    ?? null;
  const selectedList = data?.targetLists?.find((item) => item.listId === selectedListId)
    ?? data?.targetLists?.[0]
    ?? null;

  async function handleResolve(status) {
    if (!selectedAlert || !data?.viewer?.canWrite) return;
    setSaving(true);
    setFeedback("");
    try {
      const updated = await resolveReviewAlert(selectedAlert.alertId, { status, note: resolutionNote || null });
      setState((current) => ({ ...current, data: { ...current.data, reviewAlerts: current.data.reviewAlerts.map((item) => item.alertId === updated.alertId ? updated : item) } }));
      const history = await loadReviewAlertHistory(selectedAlert.alertId);
      setAlertHistory(history.items ?? []);
      setResolutionNote("");
      setFeedback(status === "completed" ? "재검토 알림을 처리 완료했습니다." : "이번 알림을 제외했습니다.");
    } catch (error) {
      setFeedback(error.message);
    } finally {
      setSaving(false);
    }
  }

  function changeTab(key) {
    setSelectedTab(key);
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.delete("tab");
      next.delete("planId");
      return next;
    });
  }

  if (state.status === "loading") return <Skeleton rows={8} columns={6} />;
  if (state.status === "error") return <ErrorState title="운영 이력을 불러오지 못했습니다" message={state.error.message} />;

  return <div className="-mx-4 -my-5 min-h-[calc(100vh-3.5rem)] bg-white px-4 py-4 sm:-mx-5 sm:px-5 md:-mx-6 md:px-6 xl:-mx-7 xl:px-7">
    <GlobalWorkflowStepper steps={workflowSteps} currentStep={5} />

    <div className="mt-3 flex flex-wrap justify-end gap-2">
      <Select value={regionFilter} onChange={setRegionFilter} options={["전체", ...regions]} render={(value) => value === "전체" ? "권역 전체" : value} />
      <Select value={assigneeFilter} onChange={setAssigneeFilter} options={["전체", ...assignees.map(([subject]) => subject)]} render={(value) => value === "전체" ? "담당자 전체" : assignees.find(([subject]) => subject === value)?.[1] ?? value} />
      <Select value={statusFilter} onChange={setStatusFilter} options={["전체", "overdue", "today", "upcoming", "completed", "dismissed"]} render={(value) => ({ 전체: "상태 전체", overdue: "기한 경과", today: "오늘 마감", upcoming: "예정", completed: "처리 완료", dismissed: "제외" })[value]} />
      <Select value={typeFilter} onChange={setTypeFilter} options={["전체", ...riskTypes]} render={(value) => value === "전체" ? "유형 전체" : value} />
    </div>

    <section className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric label="판단 완료" value={`${data.decisionHistory.filter((item) => item.action !== "deleted").length}건`} icon="◎" />
      <Metric label="저장 운영안" value={`${data.actionPlans.length}개`} icon="▤" />
      <Metric label="오늘 재검토" value={`${todayCount}명`} note={overdueCount > 0 ? `기한 경과 ${overdueCount}명` : "기한 경과 없음"} tone="warn" icon="◷" />
      <Metric label="접촉 기록" value={`${data.interactions.length}건`} icon="▢" />
    </section>

    <section className="mt-4 overflow-hidden rounded-xl border border-[#DDE4DF] bg-white">
      <div className="flex flex-wrap border-b border-[#DDE4DF] px-3 pt-1">{tabs.map(([key, label]) => <button key={key} type="button" onClick={() => changeTab(key)} className={`min-h-12 border-b-2 px-5 text-sm font-bold ${active === key ? "border-[#08735A] text-[#075C45]" : "border-transparent text-[#66736C]"}`}>{label}</button>)}</div>
      {active === "due" ? <div className="grid xl:grid-cols-[minmax(0,1.35fr)_minmax(410px,0.9fr)]">
        <AlertTable rows={rows} selectedId={selectedAlert?.alertId} onSelect={setSelectedAlertId} />
        <AlertDetail alert={selectedAlert} profile={selectedAlert ? reviewerById.get(selectedAlert.reviewerUserId) : null} alertHistory={alertHistory} decisionHistory={data.decisionHistory} interactions={data.interactions} targetLists={data.targetLists} plans={data.actionPlans} canWrite={data.viewer.canWrite} resolutionNote={resolutionNote} onNoteChange={setResolutionNote} onResolve={handleResolve} saving={saving} feedback={feedback} />
      </div> : active === "plans" ? <PlanWorkspace rows={rows} selected={selectedPlan} onSelect={setSelectedPlanId} targetLists={data.targetLists} />
        : active === "lists" ? <TargetListWorkspace rows={rows} selected={selectedList} onSelect={setSelectedListId} plans={data.actionPlans} />
          : <HistoryTable type={active} rows={rows} highlightedPlanId={highlightedPlanId} />}
    </section>

    <div className="mt-4 grid gap-3 md:grid-cols-3"><Notice title="서버 저장 기준" text="판단·재검토·접촉·운영안은 서버의 최신 저장값을 표시합니다." /><Notice title="감사 로그 (Append-Only)" text="알림과 판단 변경 이력은 수정·삭제하지 않고 추가 방식으로 기록합니다." /><Notice title="알림 정책 안내" text="현재 이메일·푸시 자동 알림은 제공하지 않으며 서비스 내부 재검토 업무만 표시합니다." /></div>
  </div>;
}

function AlertTable({ rows, selectedId, onSelect }) {
  return <div className="overflow-x-auto border-r border-[#DDE4DF]"><table className="w-full min-w-[760px] text-left text-xs"><thead className="bg-[#F6F8F6] text-[#66736C]"><tr>{["재검토 시점", "상태", "리뷰어", "지역", "관리자 판단", "담당자"].map((item) => <th key={item} className="px-4 py-3 font-bold">{item}</th>)}</tr></thead><tbody className="divide-y divide-[#E7ECE8]">{rows.length === 0 ? <tr><td colSpan="6" className="px-4 py-20 text-center"><strong className="block text-sm text-[#536159]">재검토 일정이 설정된 판단이 없습니다.</strong><span className="mt-2 block text-[#8A948F]">Reviewer 360에서 재검토 시점을 지정하면 여기에 표시됩니다.</span></td></tr> : rows.map((row) => { const timing = alertTiming(row); return <tr key={row.alertId} onClick={() => onSelect(row.alertId)} className={`cursor-pointer ${row.alertId === selectedId ? "bg-[#EDF7F2]" : "hover:bg-[#FAFBFA]"}`}><Cell>{formatDate(row.dueAt)}</Cell><Cell><TimingBadge timing={timing} /></Cell><Cell strong>{maskId(row.reviewerUserId)}</Cell><Cell>{[row.region, row.topCity].filter(Boolean).join(" · ") || "-"}</Cell><Cell><span className={row.decision === "리뷰 다시 시작 유도" ? "font-bold text-[#D3482F]" : "font-bold text-[#075C45]"}>{row.decision}</span></Cell><Cell>{row.assignedTo?.name || "미배정"}</Cell></tr>; })}</tbody></table><div className="border-t border-[#E7ECE8] px-4 py-3 text-xs text-[#718078]">전체 {rows.length.toLocaleString()}건</div></div>;
}

function AlertDetail({ alert, profile, alertHistory, decisionHistory, interactions, targetLists, plans, canWrite, resolutionNote, onNoteChange, onResolve, saving, feedback }) {
  if (!alert) return <aside className="grid min-h-[520px] place-items-center p-6 text-center text-sm font-bold text-[#718078]">왼쪽에서 재검토 알림을 선택하세요.</aside>;
  const timing = alertTiming(alert);
  const auditRows = alertHistory.length > 0 ? alertHistory : decisionHistory.filter((item) => item.reviewerUserId === alert.reviewerUserId).slice(0, 3);
  const recentContact = interactions.find((item) => item.reviewerUserId === alert.reviewerUserId);
  const relatedLists = targetLists.filter((item) => item.memberUserIds?.includes(alert.reviewerUserId)).slice(0, 2);
  const relatedPlans = plans.filter((item) => item.reviewerUserId === alert.reviewerUserId || relatedLists.some((list) => list.listId === item.targetListId)).slice(0, 2);
  return <aside className="min-w-0 p-4">
    <div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">SELECTED ALERT</p><div className="mt-2 flex items-center gap-3"><span className="grid h-11 w-11 place-items-center rounded-full bg-[#EEF7F2] text-xl text-[#075C45]">♙</span><div><h2 className="text-lg font-black">{maskId(alert.reviewerUserId)}</h2><p className="text-xs text-[#718078]">{[alert.region, alert.topCity].filter(Boolean).join(" · ") || "권역 정보 없음"}</p></div></div></div><TimingBadge timing={timing} /></div>
    <div className="mt-4 grid grid-cols-2 overflow-hidden rounded-lg border border-[#E2E7E3]"><PanelValue label="위험 신호" value={alert.riskType || profile?.riskType} tone="red" /><PanelValue label="저장된 판단" value={alert.decision} tone={alert.decision === "리뷰 다시 시작 유도" ? "red" : "green"} /></div>
    <div className="mt-3 grid grid-cols-2 gap-3 text-xs"><InfoBlock label="메모" value={alert.note || "저장된 판단 메모가 없습니다."} /><InfoBlock label="운영 정보" value={`최근 접촉 ${recentContact ? formatDate(recentContact.contactedAt) : "없음"}\n재검토 ${formatDate(alert.dueAt)}`} /></div>
    <div className="mt-4"><h3 className="text-sm font-black">감사 이력 <span className="font-medium text-[#718078]">(최근 3건)</span></h3><div className="mt-2 overflow-hidden rounded-lg border border-[#E2E7E3]"><table className="w-full text-left text-[11px]"><thead className="bg-[#F6F8F6] text-[#718078]"><tr><th className="px-3 py-2">일시</th><th className="px-3 py-2">작업자</th><th className="px-3 py-2">작업 내용</th></tr></thead><tbody className="divide-y divide-[#EDF0EE]">{auditRows.length === 0 ? <tr><td colSpan="3" className="px-3 py-5 text-center text-[#8A948F]">저장된 감사 이력이 없습니다.</td></tr> : auditRows.slice(0, 3).map((item) => <tr key={item.historyId}><td className="px-3 py-2">{formatDate(item.changedAt)}</td><td className="px-3 py-2">{item.actor?.name || "-"}</td><td className="px-3 py-2">{alertActionLabel(item.action, item.toStatus || item.toDecision)}</td></tr>)}</tbody></table></div></div>
    {alert.status === "open" && <div className="mt-4 rounded-lg bg-[#F7F9F7] p-3"><label className="text-xs font-black" htmlFor="resolution-note">처리 메모 <span className="font-medium text-[#718078]">(선택)</span></label><textarea id="resolution-note" value={resolutionNote} onChange={(event) => onNoteChange(event.target.value)} disabled={!canWrite} placeholder="재검토 결과나 후속 확인 사항을 남기세요" className="mt-2 min-h-20 w-full resize-none rounded-lg border border-[#DDE4DF] bg-white p-3 text-xs outline-none focus:border-[#07855F] disabled:bg-[#F1F3F1]" /><div className="mt-2 grid grid-cols-2 gap-2"><button type="button" onClick={() => onResolve("dismissed")} disabled={!canWrite || saving} className="min-h-10 rounded-lg border border-[#B7D8C8] text-xs font-black text-[#075C45] disabled:text-[#A0AAA4]">이번 알림 제외</button><button type="button" onClick={() => onResolve("completed")} disabled={!canWrite || saving} className="min-h-10 rounded-lg bg-[#075C45] text-xs font-black text-white disabled:bg-[#B3BBB6]">{saving ? "저장 중…" : "알림 처리 완료"}</button></div>{!canWrite && <p className="mt-2 text-[11px] font-bold text-[#9B6500]">읽기 전용 계정은 알림을 처리할 수 없습니다.</p>}</div>}
    {feedback && <p className="mt-3 rounded-lg bg-[#EEF7F2] px-3 py-2 text-xs font-bold text-[#075C45]">{feedback}</p>}
    <Link to={`/reviewers/${encodeURIComponent(alert.reviewerUserId)}#manager-decision`} className="mt-4 flex min-h-11 items-center justify-center rounded-lg bg-[#075C45] text-sm font-black text-white">Reviewer 360에서 재검토 →</Link>
    {(relatedPlans.length > 0 || relatedLists.length > 0) && <div className="mt-4 border-t border-[#DDE4DF] pt-3"><h3 className="text-sm font-black">관련 저장 기록</h3><div className="mt-2 space-y-2">{relatedPlans.map((plan) => <Link key={`plan-${plan.planId}`} to={`/operations-history?tab=plans&planId=${plan.planId}`} className="flex justify-between rounded-lg bg-[#F7F9F7] px-3 py-2 text-xs"><span className="font-bold">{plan.actionType}</span><span className="text-[#075C45]">운영안 →</span></Link>)}{relatedLists.map((list) => <div key={`list-${list.listId}`} className="flex justify-between rounded-lg bg-[#F7F9F7] px-3 py-2 text-xs"><span className="font-bold">{list.name}</span><span className="text-[#718078]">{list.memberCount}명</span></div>)}</div></div>}
  </aside>;
}

function PlanWorkspace({ rows, selected, onSelect, targetLists }) {
  const selectedList = selected?.targetListId
    ? targetLists.find((item) => item.listId === selected.targetListId)
    : null;
  return <div className="grid min-h-[430px] xl:grid-cols-[minmax(0,1.25fr)_minmax(390px,0.75fr)]">
    <div className="min-w-0 overflow-x-auto border-r border-[#DDE4DF]">
      <table className="w-full min-w-[720px] text-left text-xs">
        <thead className="bg-[#F6F8F6] text-[#66736C]"><tr>{["운영안", "구분", "대상", "채널·콘텐츠", "상태", "수정 시각"].map((item) => <th key={item} className="px-4 py-3 font-bold">{item}</th>)}</tr></thead>
        <tbody className="divide-y divide-[#E7ECE8]">{rows.length === 0 ? <tr><td colSpan="6" className="px-4 py-20 text-center text-[#7A8780]">저장된 운영안이 없습니다.</td></tr> : rows.map((row) => {
          const target = row.reviewerUserId ?? (row.targetScope === "city" ? `${row.regionCode} · ${row.cityName}` : `${row.regionCode ?? "-"} 전체`);
          return <tr key={row.planId} onClick={() => onSelect(row.planId)} className={`cursor-pointer ${row.planId === selected?.planId ? "bg-[#EDF7F2] shadow-[inset_3px_0_0_#07855F]" : "hover:bg-[#FAFBFA]"}`}>
            <Cell strong>{row.actionType}</Cell><Cell>{row.planType === "individual" ? "개인 특별 관리" : "지역 활성화"}</Cell><Cell>{maskId(target)}</Cell><Cell>{channelLabel(row.channels)} · 콘텐츠 {row.businessIds?.length ?? 0}개</Cell><Cell><Status text={row.status} /></Cell><Cell>{formatDate(row.updatedAt)}</Cell>
          </tr>;
        })}</tbody>
      </table>
      <div className="border-t border-[#E7ECE8] px-4 py-3 text-xs text-[#718078]">전체 {rows.length.toLocaleString()}개 운영안</div>
    </div>
    <PlanDetail plan={selected} targetList={selectedList} />
  </div>;
}

function PlanDetail({ plan, targetList }) {
  if (!plan) return <EmptyDetail title="왼쪽에서 운영안을 선택하세요." />;
  const target = plan.reviewerUserId ?? (plan.targetScope === "city" ? `${plan.regionCode} · ${plan.cityName}` : `${plan.regionCode ?? "-"} 전체`);
  const designHref = plan.planType === "individual"
    ? `/playbook?mode=individual&reviewer=${encodeURIComponent(plan.reviewerUserId)}`
    : `/playbook?mode=region&scope=${plan.targetScope ?? "region"}&region=${encodeURIComponent(plan.regionCode)}${plan.targetScope === "city" && plan.cityKey ? `&city=${encodeURIComponent(plan.cityKey)}` : ""}`;
  return <aside className="min-w-0 p-5">
    <div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">SELECTED OPERATION PLAN</p><h2 className="mt-1 text-lg font-black">{plan.actionType}</h2><p className="mt-1 text-xs text-[#718078]">{plan.planType === "individual" ? "개인 특별 관리" : "지역 활성화 캠페인"} · {maskId(target)}</p></div><Status text={plan.status} /></div>
    <div className="mt-4 grid grid-cols-3 overflow-hidden rounded-lg border border-[#E2E7E3]"><PanelValue label="관리자 판단" value={plan.managerDecision} tone="green" /><PanelValue label="전달 채널" value={`${plan.channels?.length ?? 0}개`} tone="green" /><PanelValue label="추천 콘텐츠" value={`${plan.businessIds?.length ?? 0}개`} tone="green" /></div>
    <DetailSection title="전달 구성"><div className="flex flex-wrap gap-2">{plan.channels?.length ? plan.channels.map((item) => <Chip key={item}>{channelName(item)}</Chip>) : <span className="text-xs text-[#8A948F]">선택된 채널이 없습니다.</span>}</div></DetailSection>
    <DetailSection title="메시지"><p className="font-bold text-[#17211D]">{plan.messageTitle || "메시지 제목 미입력"}</p><p className="mt-2 whitespace-pre-line leading-5 text-[#65726B]">{plan.messageBody || "저장된 메시지 본문이 없습니다."}</p></DetailSection>
    <DetailSection title="대상·콘텐츠"><div className="grid grid-cols-2 gap-2"><InfoBlock label="연결 명단" value={targetList ? `${targetList.name} · ${targetList.memberCount}명` : "개별 대상"} /><InfoBlock label="음식점 콘텐츠" value={`${plan.businessIds?.length ?? 0}개 선택`} /></div></DetailSection>
    <DetailSection title="30·60·90일 측정 계획"><div className="grid grid-cols-3 gap-2">{[30, 60, 90].map((day) => { const items = plan.milestones?.filter((item) => item.dayOffset === day) ?? []; return <div key={day} className="rounded-lg bg-[#F6F8F6] p-3"><strong className="text-sm text-[#075C45]">{day}일</strong><p className="mt-1 text-[11px] leading-4 text-[#65726B]">{items.map((item) => item.metricLabel).join(" · ") || "측정 항목 미설정"}</p></div>; })}</div></DetailSection>
    <div className="mt-5 grid grid-cols-2 gap-2"><Link to={designHref} className="flex min-h-11 items-center justify-center rounded-lg bg-[#075C45] text-sm font-black text-white">운영안 설계에서 수정 →</Link>{targetList ? <button type="button" className="min-h-11 rounded-lg border border-[#B7D8C8] text-sm font-black text-[#075C45]">대상 명단 {targetList.memberCount}명</button> : <Link to={plan.planType === "individual" ? `/reviewers/${encodeURIComponent(plan.reviewerUserId)}` : "/"} className="flex min-h-11 items-center justify-center rounded-lg border border-[#B7D8C8] text-sm font-black text-[#075C45]">대상 근거 확인 →</Link>}</div>
    <p className="mt-3 text-[10px] text-[#8A948F]">마지막 수정 {formatDate(plan.updatedAt)} · {plan.updatedBy?.name || "운영자"}</p>
  </aside>;
}

function TargetListWorkspace({ rows, selected, onSelect, plans }) {
  const relatedPlans = selected ? plans.filter((item) => item.targetListId === selected.listId) : [];
  return <div className="grid min-h-[410px] xl:grid-cols-[minmax(0,1.25fr)_minmax(390px,0.75fr)]">
    <div className="min-w-0 overflow-x-auto border-r border-[#DDE4DF]"><table className="w-full min-w-[650px] text-left text-xs"><thead className="bg-[#F6F8F6] text-[#66736C]"><tr>{["명단", "판단", "대상 수", "작성자", "저장 시각"].map((item) => <th key={item} className="px-4 py-3 font-bold">{item}</th>)}</tr></thead><tbody className="divide-y divide-[#E7ECE8]">{rows.length === 0 ? <tr><td colSpan="5" className="px-4 py-20 text-center text-[#7A8780]">저장된 대상 명단이 없습니다.</td></tr> : rows.map((row) => <tr key={row.listId} onClick={() => onSelect(row.listId)} className={`cursor-pointer ${row.listId === selected?.listId ? "bg-[#EDF7F2] shadow-[inset_3px_0_0_#07855F]" : "hover:bg-[#FAFBFA]"}`}><Cell strong>{row.name}</Cell><Cell>{row.decision}</Cell><Cell>{row.memberCount}명</Cell><Cell>{row.createdBy?.name}</Cell><Cell>{formatDate(row.createdAt)}</Cell></tr>)}</tbody></table><div className="border-t border-[#E7ECE8] px-4 py-3 text-xs text-[#718078]">전체 {rows.length.toLocaleString()}개 명단</div></div>
    <aside className="min-w-0 p-5">{!selected ? <EmptyDetail title="왼쪽에서 대상 명단을 선택하세요." /> : <><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">SELECTED TARGET LIST</p><h2 className="mt-1 text-lg font-black">{selected.name}</h2><p className="mt-1 text-xs text-[#718078]">{selected.modelVersion} · {formatDate(selected.createdAt)}</p></div><span className="rounded-full bg-[#EEF7F2] px-3 py-1 text-sm font-black text-[#075C45]">{selected.memberCount}명</span></div><div className="mt-4 grid grid-cols-2 overflow-hidden rounded-lg border border-[#E2E7E3]"><PanelValue label="저장 판단" value={selected.decision} tone="green" /><PanelValue label="연결 운영안" value={`${relatedPlans.length}개`} tone="green" /></div><DetailSection title="명단 구성"><div className="flex flex-wrap gap-2">{selected.memberUserIds?.slice(0, 8).map((item) => <Chip key={item}>{maskId(item)}</Chip>)}{selected.memberCount > 8 && <Chip>외 {selected.memberCount - 8}명</Chip>}</div></DetailSection><DetailSection title="연결된 운영안">{relatedPlans.length ? <div className="space-y-2">{relatedPlans.map((plan) => <Link key={plan.planId} to={`/operations-history?tab=plans&planId=${plan.planId}`} className="flex items-center justify-between rounded-lg bg-[#F6F8F6] px-3 py-3 text-xs"><span className="font-black">{plan.actionType}</span><span className="text-[#075C45]">상세 확인 →</span></Link>)}</div> : <p className="text-xs text-[#8A948F]">이 명단에 연결된 운영안이 없습니다.</p>}</DetailSection><Link to="/playbook" className="mt-5 flex min-h-11 items-center justify-center rounded-lg bg-[#075C45] text-sm font-black text-white">운영안 설계에서 활용 →</Link><p className="mt-3 text-[10px] text-[#8A948F]">작성자 {selected.createdBy?.name || "운영자"}</p></>}</aside>
  </div>;
}

function EmptyDetail({ title }) { return <div className="grid min-h-[330px] place-items-center text-center"><div><span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-[#EEF7F2] text-xl text-[#075C45]">◎</span><p className="mt-3 text-sm font-black text-[#59675F]">{title}</p><p className="mt-1 text-xs text-[#8A948F]">선택한 기록의 구성과 후속 작업을 확인할 수 있습니다.</p></div></div>; }
function DetailSection({ title, children }) { return <section className="mt-4 border-t border-[#E2E7E3] pt-4 text-xs"><h3 className="mb-3 text-sm font-black">{title}</h3>{children}</section>; }
function Chip({ children }) { return <span className="rounded-full border border-[#CFE1D7] bg-[#F4FAF7] px-2.5 py-1 text-[11px] font-bold text-[#075C45]">{children}</span>; }
function channelName(value) { return ({ app: "앱 메시지", email: "이메일", push: "푸시", phone: "전화", operator: "운영자 접촉" })[value] ?? value; }
function channelLabel(values) { return values?.length ? values.map(channelName).join(" · ") : "채널 미선택"; }

function HistoryTable({ type, rows, highlightedPlanId }) {
  return <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-xs"><thead className="bg-[#F6F8F6] text-[#66736C]"><tr>{headers(type).map((item) => <th key={item} className="px-4 py-3 font-bold">{item}</th>)}</tr></thead><tbody className="divide-y divide-[#E7ECE8]">{rows.length === 0 ? <tr><td colSpan={headers(type).length} className="px-4 py-16 text-center text-[#7A8780]">저장된 운영 기록이 없습니다.</td></tr> : rows.map((row, index) => <HistoryRow key={row.historyId ?? row.interactionId ?? row.listId ?? row.planId ?? `${row.reviewerUserId}-${index}`} type={type} row={row} highlighted={type === "plans" && String(row.planId) === highlightedPlanId} />)}</tbody></table></div>;
}

function headers(type) {
  if (type === "lists") return ["명단", "판단", "대상 수", "작성자", "저장 시각", "작업"];
  if (type === "plans") return ["운영안", "구분", "대상", "채널·콘텐츠", "상태", "수정 시각", "작업"];
  if (type === "contacts") return ["리뷰어", "채널", "접촉 시각", "기록", "담당자", "작업"];
  return ["리뷰어", "변경", "이전 판단", "저장 판단", "작업자", "변경 시각"];
}

function HistoryRow({ type, row, highlighted }) {
  if (type === "lists") return <tr><Cell strong>{row.name}</Cell><Cell>{row.decision}</Cell><Cell>{row.memberCount}명</Cell><Cell>{row.createdBy?.name}</Cell><Cell>{formatDate(row.createdAt)}</Cell><Cell><Link className="table-link" to="/playbook">운영안에서 확인 →</Link></Cell></tr>;
  if (type === "plans") { const target = row.reviewerUserId ?? (row.targetScope === "city" ? `${row.regionCode} · ${row.cityName}` : `${row.regionCode} 전체`); const designHref = row.planType === "individual" ? `/playbook?mode=individual&reviewer=${encodeURIComponent(row.reviewerUserId)}` : `/playbook?mode=region&scope=${row.targetScope ?? "region"}&region=${encodeURIComponent(row.regionCode)}${row.targetScope === "city" && row.cityKey ? `&city=${encodeURIComponent(row.cityKey)}` : ""}`; const channels = row.channels?.length ? row.channels.join(" · ") : "채널 미선택"; return <tr className={highlighted ? "bg-[#E3F1EA]" : ""}><Cell strong>{row.actionType}</Cell><Cell>{row.planType === "individual" ? "개인 특별 관리" : "지역 활성화"}</Cell><Cell>{target}</Cell><Cell>{channels} · 콘텐츠 {row.businessIds?.length ?? 0}개</Cell><Cell><Status text={row.status} /></Cell><Cell>{formatDate(row.updatedAt)}</Cell><Cell><Link className="table-link" to={designHref}>설계 확인 →</Link></Cell></tr>; }
  if (type === "contacts") return <tr><Cell strong>{maskId(row.reviewerUserId)}</Cell><Cell>{row.channel}</Cell><Cell>{formatDate(row.contactedAt)}</Cell><Cell>{row.note || "-"}</Cell><Cell>{row.actor?.name}</Cell><Cell><Link className="table-link" to={`/reviewers/${row.reviewerUserId}`}>Reviewer 360 →</Link></Cell></tr>;
  return <tr><Cell strong>{maskId(row.reviewerUserId)}</Cell><Cell>{row.action}</Cell><Cell>{row.fromDecision || "-"}</Cell><Cell>{row.toDecision || "-"}</Cell><Cell>{row.actor?.name}</Cell><Cell>{formatDate(row.changedAt)}</Cell></tr>;
}

function maskId(value) { const text = String(value ?? ""); return text.length > 12 ? `${text.slice(0, 6)}…${text.slice(-4)}` : text; }
function alertActionLabel(action, value) { return ({ created: "재검토 알림 생성", completed: "알림 처리 완료", dismissed: "알림 제외", reopened: "알림 재개", updated: "판단 수정", deleted: "판단 삭제" })[action] ?? `${action || "변경"}${value ? ` · ${value}` : ""}`; }
function Cell({ children, strong }) { return <td className={`px-4 py-3 ${strong ? "font-bold text-[#17211D]" : "text-[#59675F]"}`}>{children ?? "-"}</td>; }
function Status({ text }) { const label = { draft: "임시 저장", saved: "저장 완료", archived: "보관" }[text] ?? text; return <span className="rounded-full bg-[#E8F4EE] px-2 py-1 font-bold text-[#075C45]">{label}</span>; }
function TimingBadge({ timing }) { const tones = { red: "border-[#FF8B78] bg-[#FFF1EE] text-[#D3482F]", orange: "border-[#EFC27A] bg-[#FFF8EA] text-[#A86600]", green: "border-[#9CCDB6] bg-[#EEF7F2] text-[#075C45]", gray: "border-[#D5DBD7] bg-white text-[#66736C]" }; return <span className={`inline-flex rounded-md border px-2 py-1 text-[11px] font-black ${tones[timing.tone]}`}>{timing.label}</span>; }
function Metric({ label, value, note, tone, icon }) { return <article className="flex items-center gap-4 rounded-xl border border-[#DDE4DF] bg-white p-4"><span className={`grid h-11 w-11 place-items-center rounded-full text-lg ${tone === "warn" ? "bg-[#FFF2DF] text-[#E35D3F]" : "bg-[#EEF7F2] text-[#075C45]"}`}>{icon}</span><div><p className="text-xs font-bold text-[#6C7972]">{label}</p><p className={`mt-1 text-2xl font-black ${tone === "warn" ? "text-[#E35D3F]" : "text-[#17211D]"}`}>{value}</p>{note && <p className="mt-0.5 text-[10px] font-bold text-[#9B6500]">{note}</p>}</div></article>; }
function Select({ value, onChange, options, render }) { return <select value={value} onChange={(event) => onChange(event.target.value)} className="min-h-10 rounded-lg border border-[#D8DFDA] bg-white px-3 text-xs font-bold text-[#59675F]">{options.map((option) => <option key={option} value={option}>{render(option)}</option>)}</select>; }
function Notice({ title, text }) { return <article className="rounded-xl border border-[#DDE4DF] bg-white p-4"><p className="text-sm font-black">ⓘ {title}</p><p className="mt-2 text-xs leading-5 text-[#65726B]">{text}</p></article>; }
function PanelValue({ label, value, tone }) { return <div className="border-r border-[#E2E7E3] p-3 last:border-r-0"><p className="text-[10px] font-bold text-[#718078]">{label}</p><p className={`mt-1 text-sm font-black ${tone === "red" ? "text-[#D3482F]" : "text-[#075C45]"}`}>{value || "-"}</p></div>; }
function InfoBlock({ label, value }) { return <div className="rounded-lg bg-[#F7F9F7] p-3"><p className="font-black text-[#536159]">{label}</p><p className="mt-2 whitespace-pre-line leading-5 text-[#17211D]">{value}</p></div>; }

export default OperationsHistoryPage;
