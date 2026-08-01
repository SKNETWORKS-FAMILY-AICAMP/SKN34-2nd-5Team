import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { useOperationsSummary } from "./OperationsContext";
import {
  loadServerDecisions,
  removeServerDecision,
  saveServerDecision,
} from "../services/decisionService";

const DecisionContext = createContext(null);

export function DecisionProvider({ children }) {
  const operations = useOperationsSummary();
  const [state, setState] = useState({
    status: "loading",
    decisions: {},
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    loadServerDecisions(operations.modelVersion)
      .then(({ items }) => {
        if (cancelled) return;
        setState({
          status: "ready",
          decisions: Object.fromEntries(
            items.map((item) => [item.reviewerUserId, item]),
          ),
          error: null,
        });
      })
      .catch((error) => {
        if (!cancelled) {
          setState({ status: "error", decisions: {}, error });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [operations.modelVersion]);

  async function saveForReviewer(reviewer, changes) {
    const previous = state.decisions[reviewer.userId] ?? null;
    const changedValue = (key, fallback) =>
      Object.prototype.hasOwnProperty.call(changes, key)
        ? changes[key]
        : fallback;
    const saved = await saveServerDecision(reviewer.userId, {
      modelVersion: operations.modelVersion,
      sampleId: reviewer.sampleId,
      decision: changedValue("decision", previous?.decision),
      note: changedValue("note", previous?.note ?? null),
      assigneeSubject: changedValue(
        "assigneeSubject",
        previous?.assigneeSubject ?? null,
      ),
      snoozeUntil: changedValue("snoozeUntil", previous?.snoozeUntil ?? null),
      riskType: reviewer.riskType,
      modelJudgment: reviewer.modelJudgment,
      expectedLockVersion: previous?.lockVersion ?? null,
    });
    setState((current) => ({
      ...current,
      decisions: {
        ...current.decisions,
        [reviewer.userId]: saved,
      },
    }));
    return saved;
  }

  async function removeForReviewer(reviewerUserId) {
    await removeServerDecision(reviewerUserId);
    setState((current) => {
      const decisions = { ...current.decisions };
      delete decisions[reviewerUserId];
      return { ...current, decisions };
    });
  }

  const value = useMemo(
    () => ({
      ...state,
      saveForReviewer,
      removeForReviewer,
    }),
    // Functions intentionally close over the latest decision state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [state],
  );

  return (
    <DecisionContext.Provider value={value}>
      {children}
    </DecisionContext.Provider>
  );
}

// Context hooks intentionally live beside their provider, matching the
// existing OperationsContext module.
// eslint-disable-next-line react-refresh/only-export-components
export function useDecisions() {
  const context = useContext(DecisionContext);
  if (!context) {
    throw new Error("useDecisions must be used within DecisionProvider");
  }
  return context;
}

export function DecisionGate({ children }) {
  const context = useDecisions();
  if (context.status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-[#626D67]">
        운영 판단을 불러오는 중…
      </div>
    );
  }
  if (context.status === "error") {
    return (
      <div className="flex min-h-screen items-center justify-center p-6 text-sm text-[#8A3B2E]">
        운영 판단을 불러오지 못했습니다: {context.error.message}
      </div>
    );
  }
  return children;
}
