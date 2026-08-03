import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";

import { useReviewers } from "../../context/operations-context";

const PAGES = [
  { label: "콘텐츠 공급 위험", path: "/" },
  { label: "콘텐츠 공급 위험", path: "/regional" },
  { label: "핵심 리뷰어 관리", path: "/reviewers?mode=individual&status=미검토&sort=우선순위" },
  { label: "신규 핵심 유입", path: "/?layer=newcomers" },
  { label: "운영 결과·알림", path: "/operations-history" },
  { label: "운영안 설계", path: "/playbook" },
  { label: "운영 신뢰", path: "/trust" },
];

// Global ⌘K / Ctrl+K palette (B-12) — deterministic routing only: page
// jumps and reviewer-id lookups against data already in context. No fuzzy
// search backend, no AI guess — it's a shortcut for navigation an operator
// could already do by clicking, not a new capability.
function CommandPalette() {
  const navigate = useNavigate();
  const reviewers = useReviewers();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    function onKeyDown(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((wasOpen) => !wasOpen);
        setQuery("");
        setActiveIndex(0);
      } else if (event.key === "Escape") {
        setOpen(false);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const pageMatches = useMemo(() => {
    const q = query.trim().toLowerCase();
    return PAGES.filter((page) => page.label.toLowerCase().includes(q));
  }, [query]);

  const reviewerMatches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];
    return reviewers
      .filter((reviewer) => reviewer.userId.toLowerCase().includes(q))
      .slice(0, 6);
  }, [query, reviewers]);

  const results = useMemo(
    () => [
      ...pageMatches.map((page) => ({ kind: "page", ...page })),
      ...reviewerMatches.map((reviewer) => ({
        kind: "reviewer",
        label: reviewer.userId,
        sub: `${reviewer.priorityRank}위 · ${reviewer.riskType}`,
        path: `/reviewers/${reviewer.userId}`,
      })),
    ],
    [pageMatches, reviewerMatches],
  );

  function go(path) {
    navigate(path);
    setOpen(false);
  }

  function handleKeyDown(event) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter" && results[activeIndex]) {
      go(results[activeIndex].path);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center bg-black/40 pt-[15vh]"
      onClick={() => setOpen(false)}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-lg border border-[#DDE4DF] bg-white shadow-lg"
        onClick={(event) => event.stopPropagation()}
      >
        <input
          autoFocus
          type="text"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActiveIndex(0);
          }}
          onKeyDown={handleKeyDown}
          placeholder="리뷰어 이동, 화면 이동 · ⌘K"
          className="w-full border-b border-[#DDE4DF] px-4 py-3 text-sm outline-none"
        />

        <div className="max-h-80 overflow-y-auto p-1.5">
          {results.length === 0 && (
            <p className="px-3 py-4 text-center text-xs text-[#626D67]">
              결과 없음
            </p>
          )}

          {pageMatches.length > 0 && (
            <p className="px-3 pt-2 pb-1 text-[10px] text-[#626D67]">화면</p>
          )}
          {results.map((item, index) => (
            <button
              key={`${item.kind}-${item.path}`}
              type="button"
              onClick={() => go(item.path)}
              onMouseEnter={() => setActiveIndex(index)}
              className={[
                "flex w-full items-center gap-2 rounded px-3 py-2 text-left text-sm",
                index === activeIndex ? "bg-[#E3F1EA]" : "",
                item.kind === "reviewer" &&
                index > 0 &&
                results[index - 1]?.kind === "page"
                  ? "mt-1 border-t border-[#F1F4F1] pt-2"
                  : "",
              ].join(" ")}
            >
              <span className="flex-1 truncate">{item.label}</span>
              {item.sub && (
                <span className="shrink-0 text-xs text-[#626D67]">{item.sub}</span>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default CommandPalette;
