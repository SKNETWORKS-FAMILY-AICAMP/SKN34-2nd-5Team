import { useContext, useEffect, useMemo, useState } from "react";

import { OperationsContext } from "./operations-context";

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
      <div className="flex min-h-screen items-center justify-center text-sm text-[#68736D]">
        불러오는 중…
      </div>
    );
  }

  if (context.status === "error") {
    return (
      <div className="flex min-h-screen items-center justify-center p-6 text-sm text-[#8A3B2E]">
        데이터를 불러오지 못했습니다: {context.error.message}
      </div>
    );
  }

  return children;
}
