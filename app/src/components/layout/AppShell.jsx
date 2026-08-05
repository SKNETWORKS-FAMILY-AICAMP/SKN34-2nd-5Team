import { useState } from "react";
import { useLocation } from "react-router";

import AppSidebar from "./AppSidebar";
import AppTopbar from "./AppTopbar";

function AppShell({ children }) {
  const [collapsed, setCollapsed] = useState(() => window.localStorage.getItem("reviewer-ops-sidebar") === "collapsed");
  const { pathname } = useLocation();
  const usesWhiteCanvas = pathname === "/" || pathname === "/trust" || pathname.startsWith("/settings") || pathname.startsWith("/reviewers") || pathname.startsWith("/playbook") || pathname.startsWith("/operations-history");

  function toggleSidebar() {
    setCollapsed((current) => {
      const next = !current;
      window.localStorage.setItem("reviewer-ops-sidebar", next ? "collapsed" : "expanded");
      return next;
    });
  }

  return (
    <div className={`flex min-h-screen text-[#17211D] ${usesWhiteCanvas ? "bg-white" : "bg-[#F7F8F5]"}`}>
      <AppSidebar collapsed={collapsed} onToggle={toggleSidebar} />
      <div className="min-w-0 flex-1">
        <AppTopbar />
        <main className="mx-auto max-w-[1680px] px-4 py-5 sm:px-5 md:px-6 xl:px-7">{children}</main>
      </div>
    </div>
  );
}

export default AppShell;
