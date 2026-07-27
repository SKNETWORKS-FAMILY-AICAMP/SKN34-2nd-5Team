import { NavLink } from "react-router";

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
    label: "모델 신뢰·로드맵",
    path: "/trust",
  },
];

function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-[#DDE4DF] bg-[#F7F8F5]/95 backdrop-blur">
      <div className="mx-auto flex min-h-16 max-w-[1540px] items-center gap-6 px-6">
        <div className="min-w-48 font-bold tracking-tight text-[#17211D]">
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
                    : "border-transparent text-[#68736D] hover:text-[#137A5A]",
                ].join(" ")
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden items-center gap-2 text-xs text-[#68736D] lg:flex">
          <span className="rounded-full bg-[#17211D] px-2 py-1 font-bold text-white">
            DEMO
          </span>
          <span>React 전환 중</span>
        </div>
      </div>
    </header>
  );
}

export default Header;