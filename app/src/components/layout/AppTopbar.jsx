import { useLocation, useSearchParams } from "react-router";

import DataModeBadge from "../DataModeBadge";

const HOME_HELP = "리뷰 공급이 감소 중인 권역을 식별하고 핵심 리뷰어 운영 우선순위를 정하세요.";
const REVIEWER_HELP = "리뷰 공급 변화의 원인이 될 수 있는 리뷰어를 운영 우선순위에 따라 검토하고 관리자 판단과 실행안으로 연결합니다. 모델 점수는 확률이 아닙니다.";
const OPERATIONS_HISTORY_HELP = "저장된 판단·운영안·대상 명단과 재검토 일정을 확인합니다.";
const TRUST_HELP = "모델 점수의 의미와 데이터 시점을 공개하고 운영자가 알아야 할 한계를 검증합니다.";
const SETTINGS_HELP = "로그인 사용자와 담당 권역, 운영 권한을 관리합니다.";

const REVIEWER_SCOPE_LABELS = {
  region: "권역 종합",
  core: "핵심 리뷰어",
  newcomers: "신규 유입",
};

function pageTitle(pathname, reviewerScope = "core", playbookMode = null) {
  if (pathname === "/") return "콘텐츠 공급 위험";
  if (pathname.startsWith("/reviewers/")) return "Reviewer 360";
  if (pathname === "/reviewers") return `핵심 리뷰어 관리 / ${REVIEWER_SCOPE_LABELS[reviewerScope] ?? REVIEWER_SCOPE_LABELS.core}`;
  if (pathname === "/playbook") {
    if (playbookMode === "individual") return "운영안 설계 / 개인 특별 관리안";
    if (playbookMode === "region") return "운영안 설계 / 지역 활성화 캠페인";
    return "운영안 설계";
  }
  if (pathname === "/operations-history") return "운영 결과·알림";
  if (pathname === "/settings") return "설정 · 사용자 권한";
  if (pathname === "/trust") return "운영 신뢰";
  return "Reviewer Retention OPS";
}

function AppTopbar() {
  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
  const isHome = pathname === "/";
  const helpText = isHome
    ? HOME_HELP
    : pathname === "/reviewers"
      ? REVIEWER_HELP
      : pathname === "/operations-history"
        ? OPERATIONS_HISTORY_HELP
        : pathname === "/trust"
          ? TRUST_HELP
          : pathname === "/settings"
            ? SETTINGS_HELP
            : null;
  const playbookMode = searchParams.has("reviewer") || searchParams.get("mode") === "individual"
    ? "individual"
    : searchParams.has("region") || searchParams.get("mode") === "region"
      ? "region"
      : null;
  const title = pageTitle(pathname, searchParams.get("scope") ?? (searchParams.get("mode") === "region" ? "region" : "core"), playbookMode);

  return (
    <header aria-label="전역 도구" className="sticky top-0 z-30 flex min-h-14 items-center justify-between gap-3 border-b border-[#E1E5E2] bg-white/95 px-4 backdrop-blur sm:px-5 md:px-6 xl:px-8">
      <div className="flex min-w-0 items-center gap-2">
        <h1 className="truncate text-lg font-black tracking-[-0.02em] text-[#17211D]">{title}</h1>
        {helpText && (
          <span className="group relative shrink-0">
            <button type="button" aria-describedby="page-title-help" aria-label={`${title} 안내`} className="grid h-5 w-5 place-items-center rounded-full border border-[#AAB4AE] bg-white text-[10px] font-black text-[#66736C] transition hover:border-[#087454] hover:text-[#087454] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#087454]">i</button>
            <span id="page-title-help" role="tooltip" className="pointer-events-none absolute left-0 top-[calc(100%+10px)] z-[1000] hidden w-80 max-w-[min(20rem,calc(100vw-2rem))] rounded-lg border border-[#D7E1DB] bg-[#17211D] px-3 py-2 text-[11px] font-medium leading-5 text-white shadow-xl group-hover:block group-focus-within:block">
              {helpText}
              <span className="absolute -top-1.5 left-2.5 h-3 w-3 rotate-45 border-l border-t border-[#17211D] bg-[#17211D]" aria-hidden="true" />
            </span>
          </span>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {isHome && <span className="hidden min-h-9 items-center rounded-lg border border-[#DDE4DF] bg-white px-3 text-xs text-[#526159] md:inline-flex">비교 2017 → 선정 2018</span>}
        <button type="button" onClick={() => window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }))} className="hidden min-h-9 items-center gap-2 rounded-lg border border-[#DDE4DF] bg-white px-3 text-xs text-[#626D67] hover:border-[#9FBCAE] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#075C45] sm:flex">
          <span>검색·이동</span>
          <kbd className="rounded bg-[#F1F4F1] px-1.5 py-0.5 text-[10px]">Ctrl K</kbd>
        </button>
        <DataModeBadge />
      </div>
    </header>
  );
}

export default AppTopbar;
