import { Link, useLocation } from "react-router";

import yelpBurst from "../../assets/brand/yelp_burst.svg";
import yelpLogo from "../../assets/brand/yelp_logo.svg";
import { useAuth } from "../../features/auth/auth-context";
import { roleLabel } from "../../features/auth/rolePolicy";

const menuItems = [
  { label: "콘텐츠 공급 위험", href: "/", icon: "risk", match: ({ pathname }) => pathname === "/" },
  { label: "핵심 리뷰어 관리", href: "/reviewers?mode=individual&status=미검토&sort=우선순위", icon: "reviewer", match: ({ pathname }) => pathname.startsWith("/reviewers") },
  { label: "운영안 설계", href: "/playbook", icon: "campaign", match: ({ pathname }) => pathname === "/playbook" },
  { label: "운영 결과·알림", href: "/operations-history", icon: "history", match: ({ pathname }) => pathname === "/operations-history" },
  { label: "운영 신뢰", href: "/trust", icon: "trust", match: ({ pathname }) => pathname === "/trust" },
];

const iconPaths = {
  home: <><path d="M3 11.5 12 4l9 7.5" /><path d="M5.5 10v10h13V10M9.5 20v-6h5v6" /></>,
  risk: <><path d="M4 19V9M10 19V5M16 19v-8M22 19H2" /><path d="m3 7 4 3 4-5 4 4 6-5" /></>,
  reviewer: <><circle cx="12" cy="8" r="3.5" /><path d="M5 20c.5-4 3-6 7-6s6.5 2 7 6" /><path d="m17 5 1.2 1.2L21 3.5" /></>,
  newcomer: <><circle cx="9" cy="8" r="3" /><path d="M3 20c.4-4 2.5-6 6-6" /><path d="M16 9v8M12 13h8" /></>,
  campaign: <><path d="m4 13 13-6v10L4 13Z" /><path d="M4 13v5M17 10v4M8 15.2 9.5 21h3" /></>,
  intervention: <><path d="M4 12h7l3-6v12l3-6h3" /><path d="M4 5v14" /></>,
  trust: <><path d="M12 3 5 6v5c0 4.6 2.9 8.1 7 10 4.1-1.9 7-5.4 7-10V6l-7-3Z" /><path d="m9 12 2 2 4-4" /></>,
  history: <><path d="M4 12a8 8 0 1 0 2.3-5.7L4 8.5" /><path d="M4 4v4.5h4.5M12 7v5l3 2" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21h-4v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H3v-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3.1V3h4v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.5 1h.1v4h-.1a1.7 1.7 0 0 0-1.5 1Z" /></>,
  collapse: <><path d="m14 7-5 5 5 5" /><path d="M20 4v16" /></>,
};

function Icon({ name, className = "h-5 w-5" }) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">{iconPaths[name]}</svg>;
}

function MenuLink({ item, collapsed, routeState }) {
  const active = item.match(routeState);
  return (
    <Link to={item.href} title={collapsed ? item.label : undefined} aria-current={active ? "page" : undefined} className={`flex min-h-11 items-center rounded-xl text-sm font-semibold transition ${collapsed ? "justify-center px-2" : "gap-3 px-3"} ${active ? "bg-[#E8F4EE] text-[#075C45] shadow-[inset_3px_0_0_#0A7657]" : "text-[#4F5D56] hover:bg-[#F2F6F3] hover:text-[#075C45]"}`}>
      <Icon name={item.icon} />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </Link>
  );
}

function AppSidebar({ collapsed, onToggle }) {
  const { user, logout } = useAuth();
  const { pathname, search } = useLocation();
  const routeState = { pathname, params: new URLSearchParams(search) };

  return (
    <aside className={`sticky top-0 z-40 flex h-screen shrink-0 flex-col border-r border-[#DDE4DF] bg-white text-[#17211D] transition-[width] duration-200 ${collapsed ? "w-[76px]" : "w-[232px]"}`}>
      <div className={`flex h-20 items-center border-b border-[#E8ECE9] ${collapsed ? "justify-center px-3" : "px-5"}`}>
        <Link to="/" aria-label="콘텐츠 공급 위험" className={collapsed ? "block" : "block min-w-0"}>
          <img src={collapsed ? yelpBurst : yelpLogo} alt="Yelp" className={collapsed ? "h-9 w-9" : "h-auto w-[82px]"} />
          {!collapsed && <span className="mt-1 block text-[9px] font-black tracking-[0.11em] text-[#789086]">REVIEWER RETENTION OPS</span>}
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="주요 메뉴">
        <div className="space-y-1">{menuItems.map((item) => <MenuLink key={item.href} item={item} collapsed={collapsed} routeState={routeState} />)}</div>
        <div className="mt-4 border-t border-[#E8ECE9] pt-3">
          {user?.is_admin ? (
            <Link to="/settings" className={`flex min-h-11 items-center rounded-xl text-sm font-semibold ${pathname === "/settings" ? "bg-[#E8F4EE] text-[#075C45]" : "text-[#4F5D56] hover:bg-[#F2F6F3] hover:text-[#075C45]"} ${collapsed ? "justify-center px-2" : "gap-3 px-3"}`}><Icon name="settings" />{!collapsed && <span>설정</span>}</Link>
          ) : (
            <div title="관리자 권한 필요" aria-disabled="true" className={`flex min-h-11 items-center rounded-xl text-sm text-[#A0AAA4] ${collapsed ? "justify-center px-2" : "gap-3 px-3"}`}><Icon name="settings" />{!collapsed && <span>설정</span>}</div>
          )}
        </div>
      </nav>

      <div className="border-t border-[#E8ECE9] p-3">
        {user && <div className={`mb-2 flex items-center ${collapsed ? "justify-center" : "gap-3 px-2"}`}><span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#DFF1E8] text-xs font-black text-[#075C45]">{(user.full_name || user.username || "OP").slice(0, 2).toUpperCase()}</span>{!collapsed && <div className="min-w-0 flex-1"><p className="truncate text-xs font-bold">{user.full_name || user.username}</p><p className="truncate text-[10px] text-[#7B8781]">{roleLabel(user.access_role)}</p></div>}</div>}
        {!collapsed && user && <button type="button" onClick={logout} className="mb-1 flex min-h-9 w-full items-center rounded-lg px-3 text-xs font-semibold text-[#626D67] hover:bg-[#F2F6F3] hover:text-[#075C45]">로그아웃</button>}
        <button type="button" onClick={onToggle} className={`flex min-h-10 w-full items-center rounded-lg text-xs font-semibold text-[#7B8781] hover:bg-[#F2F6F3] hover:text-[#075C45] ${collapsed ? "justify-center" : "gap-3 px-3"}`} aria-label={collapsed ? "사이드바 펼치기" : "사이드바 접기"}><span className={collapsed ? "rotate-180" : ""}><Icon name="collapse" /></span>{!collapsed && <span>사이드바 접기</span>}</button>
      </div>
    </aside>
  );
}

export default AppSidebar;
