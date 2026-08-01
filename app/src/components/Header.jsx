import { NavLink } from "react-router";

import { useOperationsSummary } from "../context/OperationsContext";

const menuItems = [
  {
    label: "운영 홈",
    path: "/",
  },
  {
    label: "리뷰어 관리",
    path: "/reviewers",
  },
  {
    label: "리텐션 플레이북",
    path: "/playbook",
  },
  {
    label: "콘텐츠 위험",
    path: "/regional",
  },
  {
    label: "모델 신뢰",
    path: "/trust",
  },
];

function Header() {
  const operationsSummary = useOperationsSummary();

  return (
    <header className="sticky top-0 z-50 border-b border-[#DDE4DF] bg-[#F7F8F5]/95 backdrop-blur">
      <div className="mx-auto flex min-h-16 max-w-[1540px] flex-wrap items-center gap-x-6 gap-y-2 px-6 py-2">
        <div className="shrink-0 font-bold tracking-tight text-[#17211D]">
          Reviewer Retention
        </div>

        <nav className="flex flex-1 items-center gap-1 overflow-x-auto">
          {menuItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                [
                  "whitespace-nowrap border-b-2 px-3 py-5 text-sm font-semibold transition",
                  isActive
                    ? "border-[#137A5A] text-[#137A5A]"
                    : "border-transparent text-[#626D67] hover:text-[#137A5A]",
                ].join(" ")
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* The single place model version + data provenance show — every
            page eyebrow and the old header title used to repeat this. */}
        <div className="flex shrink-0 items-center gap-2 text-xs text-[#626D67]">
          <span
            className="rounded-full bg-[#17211D] px-2 py-1 font-bold text-white"
            title="화면에 표시되는 값의 출처와 모델 버전 — 실데이터 vs 데모"
          >
            {operationsSummary.dataModeLabel} DATA ·{" "}
            {operationsSummary.modelVersion.toUpperCase()}
          </span>
        </div>
      </div>
    </header>
  );
}

export default Header;