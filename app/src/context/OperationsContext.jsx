import { useContext, useEffect, useMemo, useState } from "react";

import Skeleton from "../components/common/Skeleton";
import { OperationsContext } from "./operations-context";
import yelpLogo from "../assets/brand/yelp_logo.svg";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const dataModeLabels = {
  project: "PROJECT",
  hybrid: "HYBRID",
  demo: "DEMO",
};

// operationsSummary and reviewers are both read synchronously across many
// files (Header, OperationsPage, PlaybookPage, ReviewerListPage,
// ReviewerDetailPage) — none of them can tolerate a per-page loading state
// the way the regional/trust pages do. Both are fetched together here, once,
// at the app root, and gate all rendering behind a single loading screen —
// pages below the gate can assume both values are always present, non-null.
export function OperationsProvider({ children }) {
  const [state, setState] = useState({
    status: "loading",
    data: null,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      fetch(`${API_BASE_URL}/api/operations`).then((response) => {
        if (!response.ok) {
          throw new Error(`운영 요약을 불러오지 못했습니다 (${response.status})`);
        }
        return response.json();
      }),
      fetch(`${API_BASE_URL}/api/reviewers`).then((response) => {
        if (!response.ok) {
          throw new Error(`리뷰어 목록을 불러오지 못했습니다 (${response.status})`);
        }
        return response.json();
      }),
    ])
      .then(([operationsJson, reviewersJson]) => {
        if (cancelled) return;
        setState({
          status: "ready",
          data: {
            operations: {
              ...operationsJson,
              dataModeLabel:
                dataModeLabels[operationsJson.dataMode] ??
                String(operationsJson.dataMode).toUpperCase(),
            },
            reviewers: reviewersJson,
            riskTypes: [
              ...new Set(reviewersJson.map((reviewer) => reviewer.riskType)),
            ],
          },
          error: null,
        });
      })
      .catch((error) => {
        if (!cancelled) setState({ status: "error", data: null, error });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(() => state, [state]);

  return (
    <OperationsContext.Provider value={value}>
      {children}
    </OperationsContext.Provider>
  );
}

// Renders the loading/error state itself, so screens below it never have
// to. Mirrors the OperationsProvider's status.
export function OperationsGate({ children }) {
  const context = useContext(OperationsContext);
  if (!context) {
    throw new Error("OperationsGate must be used within OperationsProvider");
  }

  if (context.status === "loading") {
    return (
      <div className="flex min-h-screen bg-[#F7F8F5] text-[#17211D]">
        <aside className="hidden w-[232px] shrink-0 border-r border-[#DDE4DF] bg-white px-5 py-6 md:block">
          <img src={yelpLogo} alt="Yelp" className="h-auto w-[82px]" />
          <p className="mt-1 text-[9px] font-bold tracking-[0.1em] text-[#789086]">REVIEWER RETENTION OPS</p>
          <div className="mt-12 space-y-3" aria-hidden="true">
            {["w-full", "w-4/5", "w-11/12", "w-3/4", "w-5/6"].map((width) => <span key={width} className={`block h-10 animate-pulse rounded-xl bg-[#EDF2EE] ${width}`} />)}
          </div>
        </aside>
        <main className="min-w-0 flex-1 px-6 py-8 md:px-8">
          <p className="text-[10px] font-bold tracking-[0.16em] text-[#789086]">YELP OPEN DATASET · RETENTION OPS</p>
          <h1 className="mt-5 text-2xl font-black">운영 데이터를 준비하고 있습니다</h1>
          <p className="mt-2 text-sm text-[#626D67]">리뷰어 코호트와 관리자 판단 정보를 안전하게 불러오는 중입니다.</p>
          <Skeleton rows={7} columns={4} className="mt-8" />
        </main>
      </div>
    );
  }

  if (context.status === "error") {
    return (
      <div className="grid min-h-screen place-items-center bg-[#F7F8F5] p-6">
        <section className="w-full max-w-lg rounded-2xl border border-[#E7C8BF] bg-white p-7 text-center shadow-sm">
          <span className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-[#FCEFEA] text-xl font-black text-[#B64B38]">!</span>
          <h1 className="mt-4 text-xl font-black text-[#17211D]">운영 데이터를 불러오지 못했습니다</h1>
          <p className="mt-3 text-sm leading-6 text-[#626D67]">MySQL과 FastAPI 실행 상태를 확인한 뒤 다시 시도해 주세요.</p>
          <p className="mt-4 rounded-lg bg-[#F7F8F5] p-3 text-left text-xs text-[#8A3B2E]">{context.error.message}</p>
          <button type="button" onClick={() => window.location.reload()} className="mt-5 min-h-11 rounded-xl bg-[#075C45] px-5 text-sm font-black text-white">다시 불러오기</button>
        </section>
      </div>
    );
  }

  return children;
}
