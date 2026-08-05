import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "../features/auth/auth-context";
import {
  cancelSponsorshipRegistration,
  createSponsorship,
  loadSponsorships,
  reactivateSponsorship,
  searchSponsorshipBusinesses,
  updateSponsorshipSchedule,
  updateSponsorshipStatus,
} from "../services/sponsorshipService";
import { SettingsSubNav } from "./SettingsPage";

const EXPIRING_SOON_DAYS = 7;
const PAGE_SIZE = 10;
const STATUS_TABS = [
  { key: "scheduled", label: "노출 예정", emptyText: "노출 예정인 스폰서 매장이 없습니다." },
  { key: "active", label: "노출 중", emptyText: "현재 노출 중인 스폰서 매장이 없습니다." },
  { key: "expired", label: "만료", emptyText: "만료된 스폰서 매장이 없습니다." },
];

function dateOffsetIso(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function daysUntil(dateString) {
  const diffMs = new Date(`${dateString}T00:00:00`) - new Date(new Date().toDateString());
  return Math.round(diffMs / (1000 * 60 * 60 * 24));
}

function SponsorshipManagementPage() {
  const { user: currentUser } = useAuth();
  const [rows, setRows] = useState([]);
  const [feedback, setFeedback] = useState(null);
  const [busyId, setBusyId] = useState(null);
  const [query, setQuery] = useState("");
  const [activeStatus, setActiveStatus] = useState("active");
  const [requestedPage, setRequestedPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [registrationOpen, setRegistrationOpen] = useState(false);
  const [businessQuery, setBusinessQuery] = useState("");
  const [businessMatches, setBusinessMatches] = useState([]);
  const [selectedBusiness, setSelectedBusiness] = useState(null);
  const [startDate, setStartDate] = useState(dateOffsetIso(0));
  const [endDate, setEndDate] = useState(dateOffsetIso(30));
  const [priorityTier, setPriorityTier] = useState("1");
  const [searchingBusinesses, setSearchingBusinesses] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [editingSponsorship, setEditingSponsorship] = useState(null);
  const [scheduleSaving, setScheduleSaving] = useState(false);

  const load = useCallback(() => {
    let cancelled = false;
    loadSponsorships()
      .then((data) => {
        if (cancelled) return;
        setRows(data.sponsorships ?? []);
      })
      .catch((error) => {
        if (cancelled) return;
        setFeedback({ tone: "error", text: error.message });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => load(), [load]);

  const filteredRows = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return rows;
    return rows.filter((row) => {
      const haystack = [row.businessName, row.businessId, row.regionState, row.businessCity]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalized);
    });
  }, [rows, query]);

  const counts = useMemo(() => STATUS_TABS.reduce((result, tab) => ({
    ...result,
    [tab.key]: rows.filter((row) => row.status === tab.key).length,
  }), {}), [rows]);

  const activeRows = useMemo(() => {
    const next = filteredRows.filter((row) => row.status === activeStatus);
    return next.sort((first, second) => {
      if (activeStatus === "scheduled") {
        return first.priorityTier - second.priorityTier
          || first.createdAt.localeCompare(second.createdAt);
      }
      if (activeStatus === "active") return first.endDate.localeCompare(second.endDate);
      return second.endDate.localeCompare(first.endDate);
    });
  }, [activeStatus, filteredRows]);

  const pageCount = Math.max(1, Math.ceil(activeRows.length / PAGE_SIZE));
  const page = Math.min(requestedPage, pageCount);
  const pageStart = (page - 1) * PAGE_SIZE;
  const pagedRows = activeRows.slice(pageStart, pageStart + PAGE_SIZE);
  const activeTab = STATUS_TABS.find((tab) => tab.key === activeStatus) ?? STATUS_TABS[0];

  if (!currentUser?.is_admin) {
    return (
      <section className="console-card p-8">
        <h1 className="console-title">스폰서 매장 관리</h1>
        <p className="mt-3 text-sm text-[#66736C]">관리자 권한이 필요합니다.</p>
      </section>
    );
  }

  async function changeStatus(sponsorshipId, status) {
    if (status === "expired" && !window.confirm("이 매장을 만료 처리하시겠습니까? 캠페인 콘텐츠에서 더 이상 노출되지 않습니다.")) return;
    setBusyId(sponsorshipId);
    setFeedback(null);
    try {
      const updated = await updateSponsorshipStatus(sponsorshipId, status);
      setRows((current) => current.map((row) => (
        row.sponsorshipId === sponsorshipId ? updated : row
      )));
      setFeedback({
        tone: "success",
        text: "스폰서 매장의 노출을 종료했습니다.",
      });
    } catch (error) {
      setFeedback({ tone: "error", text: error.message });
    } finally {
      setBusyId(null);
    }
  }

  async function reactivate(sponsorshipId) {
    setBusyId(sponsorshipId);
    setFeedback(null);
    try {
      const updated = await reactivateSponsorship(sponsorshipId);
      setRows((current) => current.map((row) => (
        row.sponsorshipId === sponsorshipId ? updated : row
      )));
      setFeedback({ tone: "success", text: "오늘부터 30일간 다시 노출하도록 등록했습니다." });
    } catch (error) {
      setFeedback({ tone: "error", text: error.message });
    } finally {
      setBusyId(null);
    }
  }

  function selectStatus(status) {
    setActiveStatus(status);
    setRequestedPage(1);
    setFeedback(null);
  }

  async function searchBusinesses() {
    if (businessQuery.trim().length < 2) {
      setFeedback({ tone: "error", text: "매장명 또는 지역을 두 글자 이상 입력하세요." });
      return;
    }
    setSearchingBusinesses(true);
    setFeedback(null);
    try {
      const data = await searchSponsorshipBusinesses(businessQuery);
      setBusinessMatches(data.businesses ?? []);
      if ((data.businesses ?? []).length === 0) {
        setFeedback({ tone: "error", text: "일치하는 Yelp 매장을 찾지 못했습니다." });
      }
    } catch (error) {
      setFeedback({ tone: "error", text: error.message });
    } finally {
      setSearchingBusinesses(false);
    }
  }

  async function submitRegistration() {
    if (!selectedBusiness) {
      setFeedback({ tone: "error", text: "등록할 Yelp 매장을 선택하세요." });
      return;
    }
    setRegistering(true);
    setFeedback(null);
    try {
      const created = await createSponsorship({
        businessId: selectedBusiness.businessId,
        startDate,
        endDate,
        priorityTier: Number(priorityTier),
      });
      setRows((current) => [created, ...current]);
      setRegistrationOpen(false);
      setSelectedBusiness(null);
      setBusinessMatches([]);
      setBusinessQuery("");
      setActiveStatus(created.status);
      setRequestedPage(1);
      setFeedback({
        tone: "success",
        text: created.status === "scheduled" ? "노출 예정 스폰서 매장을 등록했습니다." : "노출 중 스폰서 매장을 등록했습니다.",
      });
    } catch (error) {
      setFeedback({ tone: "error", text: error.message });
    } finally {
      setRegistering(false);
    }
  }

  async function submitScheduleUpdate(payload) {
    if (!editingSponsorship) return;
    setScheduleSaving(true);
    setFeedback(null);
    try {
      const updated = await updateSponsorshipSchedule(editingSponsorship.sponsorshipId, payload);
      setRows((current) => current.map((row) => (
        row.sponsorshipId === updated.sponsorshipId ? updated : row
      )));
      setEditingSponsorship(null);
      setActiveStatus(updated.status);
      setRequestedPage(1);
      setFeedback({
        tone: "success",
        text: updated.status === "scheduled" ? "노출 일정을 수정했습니다." : "노출 기간을 수정했습니다.",
      });
    } catch (error) {
      setFeedback({ tone: "error", text: error.message });
    } finally {
      setScheduleSaving(false);
    }
  }

  async function cancelRegistration(row) {
    if (!window.confirm(`${row.businessName ?? row.businessId}의 노출 예정 등록을 취소하시겠습니까?`)) return;
    setBusyId(row.sponsorshipId);
    setFeedback(null);
    try {
      await cancelSponsorshipRegistration(row.sponsorshipId);
      setRows((current) => current.filter((item) => item.sponsorshipId !== row.sponsorshipId));
      setFeedback({ tone: "success", text: "노출 예정 등록을 취소했습니다. 취소 기록은 서버에 보존됩니다." });
    } catch (error) {
      setFeedback({ tone: "error", text: error.message });
    } finally {
      setBusyId(null);
    }
  }

  function renderAction(row) {
    if (activeStatus === "scheduled") {
      return (
        <div className="flex flex-wrap gap-1.5"><button type="button" onClick={() => setEditingSponsorship(row)} className="secondary-button">일정 수정</button><button type="button" disabled={busyId === row.sponsorshipId} onClick={() => cancelRegistration(row)} className="secondary-button">{busyId === row.sponsorshipId ? "처리 중" : "등록 취소"}</button></div>
      );
    }
    if (activeStatus === "active") {
      return (
        <div className="flex flex-wrap gap-1.5"><button type="button" onClick={() => setEditingSponsorship(row)} className="secondary-button">기간 수정</button><button type="button" disabled={busyId === row.sponsorshipId} onClick={() => changeStatus(row.sponsorshipId, "expired")} className="secondary-button">{busyId === row.sponsorshipId ? "처리 중" : "노출 종료"}</button></div>
      );
    }
    return (
      <button type="button" disabled={busyId === row.sponsorshipId} onClick={() => reactivate(row.sponsorshipId)} className="secondary-button" title="오늘부터 30일간 새 노출 기간으로 다시 시작합니다.">
        {busyId === row.sponsorshipId ? "처리 중" : "다시 노출(30일 재등록)"}
      </button>
    );
  }

  return (
    <div className="space-y-4">
      <SettingsSubNav />

      <section className="console-card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-lg font-black">스폰서 매장 관리</h1>
        <p className="mt-1 text-xs leading-5 text-[#66736C]">
          오프라인 계약이 완료된 매장을 등록하고, 지역 활성화 캠페인 콘텐츠 선택 화면에 노출되는 상태를 관리합니다.
          결제·계약은 이 화면 밖에서 처리됩니다.
        </p></div><button type="button" onClick={() => setRegistrationOpen(true)} className="primary-button">+ 스폰서 매장 등록</button></div>
        <p className="mt-2 rounded-lg bg-[#FFF7E8] px-3 py-2 text-[11px] font-bold text-[#8A5A08]">
          현재 스폰서 계약·노출 정보는 기능 검증용 데모 스폰서 데이터입니다.
        </p>

        <div className="mt-4 grid gap-2 sm:grid-cols-3" role="tablist" aria-label="스폰서 매장 상태">
          {STATUS_TABS.map((tab) => {
            const selected = activeStatus === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => selectStatus(tab.key)}
                className={`flex min-h-12 items-center justify-between rounded-lg border px-4 text-left transition ${selected ? "border-[#075C45] bg-[#075C45] text-white" : "border-[#DDE4DF] bg-[#F6F8F6] text-[#526058] hover:border-[#8EB4A2]"}`}
              >
                <span className="text-xs font-black">{tab.label}</span>
                <strong className={`rounded-full px-2.5 py-1 text-xs ${selected ? "bg-white text-[#075C45]" : "bg-white text-[#17211D]"}`}>{counts[tab.key] ?? 0}</strong>
              </button>
            );
          })}
        </div>

        <label className="mt-4 block">
          <span className="sr-only">매장·권역 검색</span>
          <input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setRequestedPage(1);
            }}
            placeholder="매장명 또는 권역(예: NJ) 검색"
            className="min-h-11 w-full rounded-lg border border-[#D8DFDA] bg-white px-4 text-sm outline-none focus:border-[#168260]"
          />
        </label>
      </section>

      {feedback && (
        <p className={`rounded-lg px-4 py-3 text-xs font-bold ${feedback.tone === "error" ? "bg-[#FFF5F2] text-[#9F4A38]" : "bg-[#EAF4EF] text-[#075C45]"}`} role="status">
          {feedback.text}
        </p>
      )}

      <SponsorshipTable
        title={activeTab.label}
        rows={pagedRows}
        total={activeRows.length}
        emptyText={query.trim() ? "현재 검색 조건에 맞는 스폰서 매장이 없습니다." : activeTab.emptyText}
        renderAction={renderAction}
        loading={loading}
      />
      {!loading && activeRows.length > 0 && (
        <Pagination page={page} pageCount={pageCount} pageStart={pageStart} total={activeRows.length} onPage={setRequestedPage} />
      )}
      {registrationOpen && <RegistrationModal
        businessQuery={businessQuery}
        businessMatches={businessMatches}
        selectedBusiness={selectedBusiness}
        startDate={startDate}
        endDate={endDate}
        priorityTier={priorityTier}
        searchingBusinesses={searchingBusinesses}
        registering={registering}
        onClose={() => setRegistrationOpen(false)}
        onQueryChange={setBusinessQuery}
        onSearch={searchBusinesses}
        onSelectBusiness={setSelectedBusiness}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
        onPriorityChange={setPriorityTier}
        onSubmit={submitRegistration}
      />}
      {editingSponsorship && <ScheduleModal sponsorship={editingSponsorship} saving={scheduleSaving} onClose={() => setEditingSponsorship(null)} onSubmit={submitScheduleUpdate} />}
    </div>
  );
}

function SponsorshipTable({ title, rows, total, emptyText, renderAction, loading }) {
  return (
    <section className="console-card overflow-hidden">
      <div className="border-b border-[#DDE4DF] px-5 py-3">
        <h2 className="text-sm font-black">{title} · {total.toLocaleString()}건</h2>
      </div>
      {loading ? (
        <p className="px-5 py-10 text-center text-xs text-[#7A8780]">스폰서 매장을 불러오는 중…</p>
      ) : rows.length === 0 ? (
        <p className="px-5 py-8 text-center text-xs text-[#7A8780]">{emptyText}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-xs">
            <thead className="sticky top-0 bg-[#F6F8F6] text-[#68746D]">
              <tr>
                <th className="px-4 py-3">매장</th>
                <th>권역</th>
                <th>노출 기간</th>
                <th>우선순위</th>
                <th>등록자</th>
                <th>처리</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E7ECE8]">
              {rows.map((row) => {
                const remaining = row.status === "active" ? daysUntil(row.endDate) : null;
                const expiringSoon = remaining !== null && remaining >= 0 && remaining <= EXPIRING_SOON_DAYS;
                return (
                  <tr key={row.sponsorshipId}>
                    <td className="px-4 py-3 font-black">{row.businessName ?? row.businessId}</td>
                    <td>{row.regionState} · {row.businessCity ?? "—"}</td>
                    <td>
                      {row.startDate} ~ {row.endDate}
                      {expiringSoon && (
                        <span className="ml-2 rounded bg-[#FAEEDA] px-1.5 py-0.5 text-[9px] font-bold text-[#8A6116]">
                          만료 {remaining}일 전
                        </span>
                      )}
                    </td>
                    <td>{row.priorityTier}</td>
                    <td>{row.createdBy === "seed_business_sponsorships" ? "데모 시드" : row.createdBy}</td>
                    <td>{renderAction(row)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function RegistrationModal({
  businessQuery, businessMatches, selectedBusiness, startDate, endDate, priorityTier,
  searchingBusinesses, registering, onClose, onQueryChange, onSearch, onSelectBusiness,
  onStartDateChange, onEndDateChange, onPriorityChange, onSubmit,
}) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[#17211D]/35 p-4" role="presentation">
      <section role="dialog" aria-modal="true" aria-labelledby="sponsorship-registration-title" className="max-h-[min(720px,calc(100vh-2rem))] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-4"><div><p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">SPONSOR REGISTRATION</p><h2 id="sponsorship-registration-title" className="mt-1 text-xl font-black">스폰서 매장 등록</h2><p className="mt-1 text-xs leading-5 text-[#626D67]">시작일과 종료일에 따라 노출 예정 또는 노출 중으로 자동 분류됩니다.</p></div><button type="button" onClick={onClose} className="grid h-9 w-9 place-items-center rounded-lg border border-[#DDE4DF] text-lg text-[#526058]" aria-label="등록 창 닫기">×</button></div>
        <div className="mt-5"><label className="text-xs font-bold text-[#59675F]">Yelp 매장 검색<div className="mt-2 flex gap-2"><input value={businessQuery} onChange={(event) => onQueryChange(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); onSearch(); } }} placeholder="매장명 또는 도시·주 검색" className="min-h-11 min-w-0 flex-1 rounded-lg border border-[#DDE4DF] px-3 text-sm" /><button type="button" onClick={onSearch} disabled={searchingBusinesses} className="secondary-button">{searchingBusinesses ? "검색 중" : "검색"}</button></div></label>
          {businessMatches.length > 0 && <div className="mt-3 max-h-48 space-y-2 overflow-y-auto rounded-lg border border-[#E2E7E3] p-2">{businessMatches.map((business) => <button key={business.businessId} type="button" onClick={() => onSelectBusiness(business)} className={`w-full rounded-lg border px-3 py-2 text-left text-xs ${selectedBusiness?.businessId === business.businessId ? "border-[#075C45] bg-[#EAF4EF]" : "border-[#E2E7E3] hover:border-[#8EB4A2]"}`}><strong>{business.name}</strong><span className="ml-2 text-[#718078]">{business.state} · {business.city}</span></button>)}</div>}
          {selectedBusiness && <p className="mt-2 rounded-lg bg-[#EAF4EF] px-3 py-2 text-xs font-bold text-[#075C45]">선택: {selectedBusiness.name} · {selectedBusiness.state} {selectedBusiness.city}</p>}
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-3"><label className="text-xs font-bold text-[#59675F]">노출 시작일<input type="date" value={startDate} min={dateOffsetIso(0)} onChange={(event) => onStartDateChange(event.target.value)} className="mt-2 min-h-11 w-full rounded-lg border border-[#DDE4DF] px-3" /></label><label className="text-xs font-bold text-[#59675F]">노출 종료일<input type="date" value={endDate} min={startDate} onChange={(event) => onEndDateChange(event.target.value)} className="mt-2 min-h-11 w-full rounded-lg border border-[#DDE4DF] px-3" /></label><label className="text-xs font-bold text-[#59675F]">노출 우선순위<select value={priorityTier} onChange={(event) => onPriorityChange(event.target.value)} className="mt-2 min-h-11 w-full rounded-lg border border-[#DDE4DF] px-3">{[1, 2, 3].map((value) => <option key={value} value={value}>{value}</option>)}</select></label></div>
        <div className="mt-6 flex justify-end gap-2"><button type="button" onClick={onClose} className="secondary-button">취소</button><button type="button" onClick={onSubmit} disabled={registering || !selectedBusiness} className="primary-button">{registering ? "등록 중…" : "스폰서 매장 등록"}</button></div>
      </section>
    </div>
  );
}

function ScheduleModal({ sponsorship, saving, onClose, onSubmit }) {
  const [startDate, setStartDate] = useState(sponsorship.startDate);
  const [endDate, setEndDate] = useState(sponsorship.endDate);
  const [priorityTier, setPriorityTier] = useState(String(sponsorship.priorityTier));
  const scheduled = sponsorship.status === "scheduled";
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-[#17211D]/35 p-4" role="presentation">
      <section role="dialog" aria-modal="true" aria-labelledby="sponsorship-schedule-title" className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-4"><div><p className="text-[10px] font-black tracking-[0.12em] text-[#137A5A]">EXPOSURE SCHEDULE</p><h2 id="sponsorship-schedule-title" className="mt-1 text-xl font-black">{scheduled ? "노출 일정 수정" : "노출 기간 수정"}</h2><p className="mt-1 text-xs text-[#626D67]">{sponsorship.businessName ?? sponsorship.businessId} · {sponsorship.regionState} {sponsorship.businessCity ?? ""}</p></div><button type="button" onClick={onClose} className="grid h-9 w-9 place-items-center rounded-lg border border-[#DDE4DF] text-lg text-[#526058]" aria-label="수정 창 닫기">×</button></div>
        <div className="mt-5 grid gap-4 sm:grid-cols-3"><label className="text-xs font-bold text-[#59675F]">노출 시작일<input type="date" value={startDate} min={dateOffsetIso(0)} onChange={(event) => setStartDate(event.target.value)} className="mt-2 min-h-11 w-full rounded-lg border border-[#DDE4DF] px-3" /></label><label className="text-xs font-bold text-[#59675F]">노출 종료일<input type="date" value={endDate} min={startDate} onChange={(event) => setEndDate(event.target.value)} className="mt-2 min-h-11 w-full rounded-lg border border-[#DDE4DF] px-3" /></label><label className="text-xs font-bold text-[#59675F]">노출 우선순위<select value={priorityTier} onChange={(event) => setPriorityTier(event.target.value)} className="mt-2 min-h-11 w-full rounded-lg border border-[#DDE4DF] px-3">{[1, 2, 3].map((value) => <option key={value} value={value}>{value}</option>)}</select></label></div>
        <p className="mt-4 rounded-lg bg-[#F0F7F3] px-3 py-2 text-[11px] leading-5 text-[#4F5D56]">수정한 시작일이 미래면 노출 예정으로, 오늘이면 노출 중으로 자동 분류됩니다.</p>
        <div className="mt-6 flex justify-end gap-2"><button type="button" onClick={onClose} className="secondary-button">취소</button><button type="button" disabled={saving} onClick={() => onSubmit({ startDate, endDate, priorityTier: Number(priorityTier) })} className="primary-button">{saving ? "저장 중…" : "변경 저장"}</button></div>
      </section>
    </div>
  );
}

function Pagination({ page, pageCount, pageStart, total, onPage }) {
  const pages = Array.from(new Set(
    [1, page - 1, page, page + 1, pageCount]
      .filter((value) => value >= 1 && value <= pageCount),
  )).sort((first, second) => first - second);
  return (
    <div className="flex items-center justify-between rounded-xl border border-[#E3E8E5] bg-white px-4 py-2 text-xs">
      <div className="flex items-center gap-1">
        <button type="button" disabled={page === 1} onClick={() => onPage(page - 1)} className="grid h-8 w-8 place-items-center rounded border border-[#DDE4DF] disabled:opacity-35" aria-label="이전 페이지">‹</button>
        {pages.map((value, index) => (
          <span key={value} className="flex items-center gap-1">
            {index > 0 && value - pages[index - 1] > 1 && <span>…</span>}
            <button type="button" onClick={() => onPage(value)} className={`grid h-8 min-w-8 place-items-center rounded px-2 font-bold ${value === page ? "bg-[#075C45] text-white" : "hover:bg-[#F1F4F1]"}`} aria-current={value === page ? "page" : undefined}>{value}</button>
          </span>
        ))}
        <button type="button" disabled={page === pageCount} onClick={() => onPage(page + 1)} className="grid h-8 w-8 place-items-center rounded border border-[#DDE4DF] disabled:opacity-35" aria-label="다음 페이지">›</button>
      </div>
      <span className="text-[#626D67]">{Math.min(pageStart + 1, total).toLocaleString()}–{Math.min(pageStart + PAGE_SIZE, total).toLocaleString()} / {total.toLocaleString()}</span>
    </div>
  );
}

export default SponsorshipManagementPage;
