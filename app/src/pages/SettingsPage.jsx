import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router";

import {
  approveAdminUser,
  createAdminUser,
  createRegionAdminUsers,
  fetchAdminUsers,
  rejectAdminUser,
  resetAdminUserPassword,
  updateAdminUserRole,
  updateAdminUserStatus,
} from "../features/auth/authApi";
import { useAuth } from "../features/auth/auth-context";
import { loadRegionalRisk } from "../data";

const statusFilters = ["APPROVED", "PENDING", "SUSPENDED", "REJECTED"];
const roleFilters = ["ALL", "ADMIN", "OPERATOR", "VIEWER"];
const inputClass = "min-h-11 w-full rounded-lg border border-[#D8DFDA] bg-white px-3 text-sm outline-none focus:border-[#168260]";

function SettingsPage() {
  const { user: currentUser } = useAuth();
  const [status, setStatus] = useState("APPROVED");
  const [roleFilter, setRoleFilter] = useState("ALL");
  const [query, setQuery] = useState("");
  const [users, setUsers] = useState([]);
  const [regions, setRegions] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [panelMode, setPanelMode] = useState("edit");
  const [message, setMessage] = useState("");
  const [credentials, setCredentials] = useState([]);

  const load = useCallback(
    () =>
      fetchAdminUsers(status).then((data) => {
        setUsers(data.items);
        setSelectedId((current) =>
          data.items.some((item) => item.id === current)
            ? current
            : data.items[0]?.id ?? null,
        );
      }),
    [status],
  );

  useEffect(() => {
    load().catch((error) => setMessage(error.message));
  }, [load]);

  useEffect(() => {
    loadRegionalRisk()
      .then((data) =>
        setRegions(
          [...(data.regions ?? [])]
            .map((item) => ({ code: item.region, city: item.topCity }))
            .sort((a, b) => a.code.localeCompare(b.code)),
        ),
      )
      .catch((error) => setMessage(`권역 목록을 불러오지 못했습니다. ${error.message}`));
  }, []);

  const selected = useMemo(
    () => users.find((item) => item.id === selectedId) ?? null,
    [selectedId, users],
  );
  const visibleUsers = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return users.filter((item) => {
      const matchesRole = roleFilter === "ALL" || item.access_role === roleFilter;
      const haystack = [item.full_name, item.username, item.email, item.region_code]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return matchesRole && (!normalized || haystack.includes(normalized));
    });
  }, [query, roleFilter, users]);

  if (!currentUser?.is_admin) {
    return (
      <section className="console-card p-8">
        <h1 className="console-title">설정</h1>
        <p className="mt-3 text-sm text-[#66736C]">관리자 권한이 필요합니다.</p>
      </section>
    );
  }

  async function act(action, successMessage = "변경 사항을 저장했습니다.") {
    setMessage("");
    try {
      const result = await action();
      await load();
      setMessage(successMessage);
      return result;
    } catch (error) {
      setMessage(error.message);
      throw error;
    }
  }

  function selectUser(userId) {
    setSelectedId(userId);
    setPanelMode("edit");
    setCredentials([]);
  }

  return (
    <div className="space-y-4">
      <SettingsSubNav />
      <header className="flex flex-wrap items-end justify-end gap-4">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => { setPanelMode("create"); setCredentials([]); }}
            className="secondary-button"
          >
            사용자 추가
          </button>
          <button
            type="button"
            onClick={() => { setPanelMode("bulk"); setCredentials([]); }}
            className="primary-button"
          >
            14개 권역 계정 일괄 생성
          </button>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(390px,0.7fr)]">
        <section className="console-card min-w-0 overflow-hidden">
          <div className="flex flex-wrap items-center gap-2 border-b border-[#DDE4DF] p-4">
            <label className="relative min-w-[240px] flex-1">
              <span className="sr-only">사용자 검색</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="이름, 아이디, 권역 검색"
                className="min-h-11 w-full rounded-lg border border-[#D8DFDA] bg-white px-4 text-sm outline-none focus:border-[#168260]"
              />
            </label>
            <select
              value={roleFilter}
              onChange={(event) => setRoleFilter(event.target.value)}
              className="min-h-11 rounded-lg border border-[#D8DFDA] bg-white px-3 text-xs font-bold"
            >
              {roleFilters.map((item) => <option key={item} value={item}>{roleLabel(item)}</option>)}
            </select>
          </div>
          <div className="flex flex-wrap gap-2 border-b border-[#DDE4DF] px-4 py-3">
            {statusFilters.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setStatus(item)}
                className={`rounded-full px-4 py-2 text-xs font-bold ${status === item ? "bg-[#075C45] text-white" : "bg-[#F2F5F3] text-[#526058]"}`}
              >
                {labelStatus(item)}
              </button>
            ))}
            <span className="ml-auto self-center text-xs text-[#718078]">{visibleUsers.length}명</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-xs">
              <thead className="bg-[#F6F8F6] text-[#68746D]">
                <tr>
                  <th className="px-4 py-3">이름</th>
                  <th>아이디</th>
                  <th>역할</th>
                  <th>담당 권역</th>
                  <th>상태</th>
                  <th>최근 로그인</th>
                  <th>관리</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E7ECE8]">
                {visibleUsers.map((item) => (
                  <tr key={item.id} className={item.id === selectedId && panelMode === "edit" ? "bg-[#EDF7F2]" : "hover:bg-[#FAFBFA]"}>
                    <td className="px-4 py-3 font-black">{item.full_name}</td>
                    <td>{item.username || item.email}</td>
                    <td><RoleBadge role={item.access_role} /></td>
                    <td>{item.region_code || "전체"}</td>
                    <td><StatusBadge status={item.status} /></td>
                    <td>{formatDateTime(item.last_login_at)}</td>
                    <td><button type="button" onClick={() => selectUser(item.id)} className="table-link">편집</button></td>
                  </tr>
                ))}
                {visibleUsers.length === 0 && (
                  <tr><td colSpan="7" className="px-4 py-16 text-center text-sm text-[#7A8780]">조건에 맞는 사용자가 없습니다.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="console-card p-5">
          {panelMode === "create" ? (
            <CreateUserPanel
              regions={regions}
              onCancel={() => setPanelMode("edit")}
              onCreated={async (payload) => {
                const result = await act(() => createAdminUser(payload), "계정을 생성했습니다. 임시 비밀번호를 안전하게 전달하세요.");
                setCredentials([result]);
                setStatus("APPROVED");
              }}
            />
          ) : panelMode === "bulk" ? (
            <BulkRegionPanel
              regions={regions}
              onCancel={() => setPanelMode("edit")}
              onCreated={async (regionCodes) => {
                const result = await act(() => createRegionAdminUsers(regionCodes), `${regionCodes.length}개 권역 계정을 생성했습니다.`);
                setCredentials(result.items);
                setStatus("APPROVED");
              }}
            />
          ) : selected ? (
            <UserEditor key={selected.id} user={selected} regions={regions} act={act} />
          ) : (
            <p className="text-sm text-[#7A8780]">사용자를 선택하세요.</p>
          )}
          {credentials.length > 0 && <CredentialResult credentials={credentials} />}
        </section>
      </div>

      {message && <p className="rounded-lg bg-[#E8F4EE] px-4 py-3 text-xs font-bold text-[#075C45]">{message}</p>}

      <PermissionMatrix />
      <SecurityGuide />
    </div>
  );
}

function CreateUserPanel({ regions, onCancel, onCreated }) {
  const [form, setForm] = useState(() => emptyUserForm());
  const [submitting, setSubmitting] = useState(false);
  const operator = form.access_role === "OPERATOR";

  function change(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }
  function presetViewer() {
    setForm({
      ...emptyUserForm(),
      username: "retention_viewer",
      full_name: "공용 조회 전용",
      password: randomPassword(),
      access_role: "VIEWER",
      region_code: "",
    });
  }
  async function submit(event) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await onCreated({
        ...form,
        email: form.email || null,
        region_code: operator ? form.region_code : null,
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <PanelHeader title="사용자 추가" onCancel={onCancel} />
      <button type="button" onClick={presetViewer} className="w-full rounded-lg border border-[#A9D1BE] bg-[#F1F8F4] px-3 py-2 text-xs font-black text-[#075C45]">공용 조회 전용 계정으로 채우기</button>
      <Field label="이름"><input required value={form.full_name} onChange={(event) => change("full_name", event.target.value)} className={inputClass} /></Field>
      <Field label="아이디"><input required value={form.username} onChange={(event) => change("username", event.target.value)} className={inputClass} /></Field>
      <Field label="이메일(선택)"><input type="email" value={form.email} onChange={(event) => change("email", event.target.value)} className={inputClass} /></Field>
      <Field label="임시 비밀번호">
        <div className="flex gap-2"><input required minLength="10" value={form.password} onChange={(event) => change("password", event.target.value)} className={`${inputClass} min-w-0 flex-1`} /><button type="button" onClick={() => change("password", randomPassword())} className="secondary-button shrink-0">자동 생성</button></div>
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="역할"><select value={form.access_role} onChange={(event) => change("access_role", event.target.value)} className={inputClass}><option value="OPERATOR">운영자</option><option value="VIEWER">조회 전용</option></select></Field>
        <Field label="담당 권역"><select required={operator} disabled={!operator} value={form.region_code} onChange={(event) => change("region_code", event.target.value)} className={`${inputClass} disabled:bg-[#F2F4F2]`}><option value="">{operator ? "선택" : "전체"}</option>{regions.map((region) => <option key={region.code} value={region.code}>{region.code} · {region.city}</option>)}</select></Field>
      </div>
      <label className="flex items-center gap-2 text-xs font-bold"><input type="checkbox" checked={form.must_change_password} onChange={(event) => change("must_change_password", event.target.checked)} />최초 로그인 시 비밀번호 변경</label>
      <button disabled={submitting} type="submit" className="primary-button w-full disabled:opacity-50">{submitting ? "생성 중" : "계정 생성"}</button>
    </form>
  );
}

function BulkRegionPanel({ regions, onCancel, onCreated }) {
  const [excluded, setExcluded] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const selected = regions.map((region) => region.code).filter((code) => !excluded.includes(code));
  function toggle(code) { setExcluded((current) => current.includes(code) ? current.filter((item) => item !== code) : [...current, code]); }
  async function submit() {
    setSubmitting(true);
    try { await onCreated(selected); } finally { setSubmitting(false); }
  }
  return (
    <div className="space-y-4">
      <PanelHeader title="권역 계정 일괄 생성" onCancel={onCancel} />
      <p className="text-xs leading-5 text-[#66736C]">실제 권역 데이터에서 운영자 계정을 생성합니다. 아이디는 <strong>region_권역_ops</strong> 형식이며 임시 비밀번호는 한 번만 표시됩니다.</p>
      <div className="grid grid-cols-2 gap-2">
        {regions.map((region) => <label key={region.code} className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-xs ${selected.includes(region.code) ? "border-[#79B79B] bg-[#EDF7F2]" : "border-[#DDE4DF]"}`}><input type="checkbox" checked={selected.includes(region.code)} onChange={() => toggle(region.code)} /><span className="font-black">{region.code}</span><span className="truncate text-[#718078]">{region.city}</span></label>)}
      </div>
      <div className="flex items-center justify-between text-xs"><span>선택 {selected.length}개</span><button type="button" onClick={() => setExcluded([])} className="table-link">전체 선택</button></div>
      <button disabled={!selected.length || submitting} type="button" onClick={submit} className="primary-button w-full disabled:opacity-50">{submitting ? "생성 중" : `${selected.length}개 권역 계정 생성`}</button>
    </div>
  );
}

function UserEditor({ user, regions, act }) {
  const [role, setRole] = useState(user.access_role === "VIEWER" ? "VIEWER" : "OPERATOR");
  const [region, setRegion] = useState(user.region_code || "");
  const active = user.status === "APPROVED";
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3"><div><p className="console-kicker">USER PERMISSION</p><h2 className="mt-1 text-lg font-black">사용자 권한 편집</h2></div><StatusBadge status={user.status} /></div>
      <div className="grid grid-cols-2 gap-3 rounded-xl bg-[#F6F8F6] p-4"><Info label="이름" value={user.full_name} /><Info label="아이디" value={user.username || user.email} /><Info label="역할" value={roleLabel(user.access_role)} /><Info label="최근 로그인" value={formatDateTime(user.last_login_at)} /></div>
      {user.is_admin ? <p className="rounded-lg bg-[#FFF7E8] px-3 py-3 text-xs text-[#805F22]">관리자 계정은 서버 CLI에서만 생성·변경할 수 있습니다.</p> : <>
        <div className="grid grid-cols-2 gap-3">
          <Field label="역할"><select value={role} onChange={(event) => setRole(event.target.value)} className={inputClass}><option value="OPERATOR">운영자</option><option value="VIEWER">조회 전용</option></select></Field>
          <Field label="담당 권역"><select disabled={role === "VIEWER"} value={role === "VIEWER" ? "" : region} onChange={(event) => setRegion(event.target.value)} className={`${inputClass} disabled:bg-[#F2F4F2]`}><option value="">{role === "VIEWER" ? "전체" : "선택"}</option>{regions.map((item) => <option key={item.code} value={item.code}>{item.code} · {item.city}</option>)}</select></Field>
        </div>
        {user.status === "PENDING" ? <div className="flex gap-2"><button type="button" disabled={role === "OPERATOR" && !region} onClick={() => act(() => approveAdminUser(user.id, role, role === "OPERATOR" ? region : null, "설정 화면 승인"))} className="primary-button flex-1 disabled:opacity-50">가입 승인</button><button type="button" onClick={() => act(() => rejectAdminUser(user.id, "설정 화면 거절"))} className="secondary-button text-[#B44B39]">거절</button></div> : <>
          {active && <button type="button" disabled={role === "OPERATOR" && !region} onClick={() => act(() => updateAdminUserRole(user.id, role, role === "OPERATOR" ? region : null, "설정 화면 권한 변경"))} className="primary-button w-full disabled:opacity-50">권한 저장</button>}
          {(user.status === "APPROVED" || user.status === "SUSPENDED") && <div className="flex items-center justify-between rounded-lg border border-[#DDE4DF] px-3 py-3"><div><p className="text-xs font-black">계정 상태</p><p className="mt-1 text-[10px] text-[#7A8780]">비활성화하면 현재 로그인 세션도 종료됩니다.</p></div><button type="button" onClick={() => act(() => updateAdminUserStatus(user.id, !active, active ? "관리자 비활성화" : "관리자 재활성화"), active ? "계정을 비활성화했습니다." : "계정을 활성화했습니다.")} className={active ? "secondary-button text-[#B44B39]" : "primary-button"}>{active ? "비활성화" : "활성화"}</button></div>}
          {(user.status === "APPROVED" || user.status === "SUSPENDED") && <PasswordResetPanel user={user} act={act} />}
        </>}
      </>}
    </div>
  );
}

function PasswordResetPanel({ user, act }) {
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const valid = password.length >= 10;

  async function submit() {
    setSubmitting(true);
    try {
      await act(
        () => resetAdminUserPassword(user.id, password, "설정 화면에서 비밀번호 재설정"),
        "비밀번호를 재설정했습니다. 다음 로그인 시 비밀번호 변경이 요구됩니다.",
      );
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-lg border border-[#DDE4DF] px-3 py-3">
      <p className="text-xs font-black">비밀번호 재설정</p>
      <p className="mt-1 text-[10px] text-[#7A8780]">재설정하면 현재 로그인 세션이 모두 종료되고, 다음 로그인 시 비밀번호 변경이 요구됩니다.</p>
      <div className="mt-2 flex gap-2">
        <input
          type="text"
          minLength="10"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="새 비밀번호 (10자 이상)"
          className={`${inputClass} min-w-0 flex-1 font-mono`}
        />
        <button type="button" onClick={() => setPassword(randomPassword())} className="secondary-button shrink-0">자동 생성</button>
      </div>
      <button type="button" disabled={!valid || submitting} onClick={submit} className="primary-button mt-2 w-full disabled:opacity-50">
        {submitting ? "저장 중…" : "비밀번호 재설정"}
      </button>
    </div>
  );
}

function CredentialResult({ credentials }) {
  const rows = credentials.map((item) => ({ name: item.user.full_name, username: item.user.username, region: item.user.region_code || "전체", role: roleLabel(item.user.access_role), password: item.temporary_password }));
  function download() {
    const header = "name,username,region,role,temporary_password";
    const csv = [header, ...rows.map((row) => [row.name, row.username, row.region, row.role, row.password].map(csvCell).join(","))].join("\n");
    const url = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `retention-accounts-${new Date().toISOString().slice(0, 10)}.csv`; anchor.click(); URL.revokeObjectURL(url);
  }
  return <div className="mt-5 border-t border-[#DDE4DF] pt-4"><div className="flex items-center justify-between gap-2"><div><h3 className="text-sm font-black">생성된 계정 {rows.length}개</h3><p className="mt-1 text-[10px] text-[#B04A35]">임시 비밀번호는 이 화면을 닫으면 다시 표시되지 않습니다.</p></div><button type="button" onClick={download} className="secondary-button">CSV 저장</button></div><div className="mt-3 max-h-56 overflow-auto rounded-lg border border-[#DDE4DF]"><table className="w-full text-left text-[11px]"><thead className="sticky top-0 bg-[#F5F7F5]"><tr><th className="px-3 py-2">권역</th><th>아이디</th><th>임시 비밀번호</th></tr></thead><tbody className="divide-y divide-[#E7ECE8]">{rows.map((row) => <tr key={row.username}><td className="px-3 py-2 font-black">{row.region}</td><td>{row.username}</td><td className="font-mono">{row.password}</td></tr>)}</tbody></table></div></div>;
}

function PermissionMatrix() {
  const rows = [["콘텐츠 공급 위험 조회", true, true, true], ["핵심 리뷰어 판단 저장", true, "담당 권역", false], ["운영안·대상 명단 저장", true, "담당 권역", false], ["사용자·권한 관리", true, false, false]];
  return <section className="console-card overflow-hidden"><div className="border-b border-[#DDE4DF] p-5"><h2 className="font-black">역할별 권한</h2><p className="mt-1 text-xs text-[#718078]">역할에 포함된 권한이며 개별 권한은 역할에 따라 자동으로 적용됩니다.</p></div><div className="overflow-x-auto"><table className="w-full min-w-[640px] text-center text-xs"><thead className="bg-[#F6F8F6]"><tr><th className="px-4 py-3 text-left">권한</th><th>관리자</th><th>운영자</th><th>조회 전용</th></tr></thead><tbody className="divide-y divide-[#E7ECE8]">{rows.map(([label, admin, operator, viewer]) => <tr key={label}><td className="px-4 py-3 text-left font-bold">{label}</td><Permission value={admin} /><Permission value={operator} /><Permission value={viewer} /></tr>)}</tbody></table></div></section>;
}

function SecurityGuide() { return <section className="console-card p-5"><h2 className="font-black">인증·보안 안내</h2><div className="mt-4 grid gap-4 text-xs text-[#66736C] md:grid-cols-3"><Guide title="세션 동작" text="세션은 8시간 유지됩니다. 공용 조회 계정은 여러 기기에서 동시 로그인할 수 있습니다." /><Guide title="권역 계정" text="운영자 계정은 하나의 담당 권역을 가지며, 조회 전용 계정은 전체 권역을 조회합니다." /><Guide title="감사 추적" text="계정 생성·역할·상태 변경은 추가 방식의 감사 이력으로 기록됩니다." /></div></section>; }

export function SettingsSubNav() {
  const { pathname } = useLocation();
  const linkClass = (active) => `rounded-full px-4 py-2 text-xs font-bold ${active ? "bg-[#075C45] text-white" : "bg-[#F2F5F3] text-[#526058]"}`;
  return (
    <nav className="flex gap-2">
      <Link to="/settings" className={linkClass(pathname === "/settings")}>사용자 관리</Link>
      <Link to="/settings/sponsorships" className={linkClass(pathname === "/settings/sponsorships")}>스폰서 매장 관리</Link>
    </nav>
  );
}

function PanelHeader({ title, onCancel }) { return <div className="flex items-center justify-between"><div><p className="console-kicker">ACCOUNT PROVISIONING</p><h2 className="mt-1 text-lg font-black">{title}</h2></div><button type="button" onClick={onCancel} className="table-link">취소</button></div>; }
function Field({ label, children }) { return <label className="block text-xs font-bold text-[#59675F]">{label}<div className="mt-2">{children}</div></label>; }
function Info({ label, value }) { return <div><p className="text-[10px] font-bold text-[#7A8780]">{label}</p><p className="mt-1 truncate text-sm font-bold">{value}</p></div>; }
function Guide({ title, text }) { return <article><p className="font-black text-[#17211D]">ⓘ {title}</p><p className="mt-2 leading-5">{text}</p></article>; }
function Permission({ value }) { return <td className="px-3 py-3 font-black text-[#075C45]">{value === true ? "✓" : value === false ? "—" : value}</td>; }
function RoleBadge({ role }) { return <span className={`rounded-md px-2 py-1 font-bold ${role === "ADMIN" ? "bg-[#E7F3ED] text-[#075C45]" : role === "OPERATOR" ? "bg-[#EAF2FA] text-[#2A5E91]" : "bg-[#F2F3F2] text-[#59645E]"}`}>{roleLabel(role)}</span>; }
function StatusBadge({ status }) { return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 font-bold ${status === "APPROVED" ? "bg-[#EAF6F0] text-[#08714F]" : status === "PENDING" ? "bg-[#FFF4DF] text-[#9A6500]" : "bg-[#F4F4F4] text-[#717A75]"}`}><i className={`h-1.5 w-1.5 rounded-full ${status === "APPROVED" ? "bg-[#0D8A60]" : "bg-[#9AA39E]"}`} />{labelStatus(status)}</span>; }
function labelStatus(value) { return ({ PENDING: "승인 대기", APPROVED: "활성", REJECTED: "거절", SUSPENDED: "비활성" })[value] ?? value; }
function roleLabel(value) { return ({ ALL: "역할 전체", ADMIN: "관리자", OPERATOR: "운영자", VIEWER: "조회 전용" })[value] ?? value ?? "미지정"; }
function formatDateTime(value) { return value ? new Intl.DateTimeFormat("ko-KR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "—"; }
function emptyUserForm() { return { full_name: "", username: "", email: "", password: randomPassword(), access_role: "OPERATOR", region_code: "", must_change_password: true }; }
function randomPassword() { const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%"; const bytes = new Uint32Array(14); crypto.getRandomValues(bytes); return Array.from(bytes, (value) => chars[value % chars.length]).join(""); }
function csvCell(value) { return `"${String(value ?? "").replaceAll('"', '""')}"`; }

export default SettingsPage;
