import { createContext, useContext } from "react";

export const OperationsContext = createContext(null);

function useReadyData(hookName) {
  const context = useContext(OperationsContext);
  if (!context) {
    throw new Error(`${hookName} must be used within OperationsProvider`);
  }
  if (context.status !== "ready") {
    throw new Error(`${hookName} called before data was ready`);
  }
  return context.data;
}

// Only call these from a component rendered below <OperationsGate>
// (see App.jsx) — that gate is what guarantees status === "ready" here.
export function useOperationsSummary() {
  return useReadyData("useOperationsSummary").operations;
}

export function useReviewers() {
  return useReadyData("useReviewers").reviewers;
}

export function useRiskTypes() {
  return useReadyData("useRiskTypes").riskTypes;
}
