// Real v04 project data, exported from the Streamlit app's own core modules by
// scripts/export_frontend_data.py. Regenerate after the model or profiles change:
//
//     ./venv/Scripts/python.exe scripts/export_frontend_data.py
//
// These files stand in for the FastAPI/MySQL layer that is not built yet, so the
// screens read real reviewer records instead of synthetic ones.
import operationsJson from "./operations.json";
import playbooksJson from "./playbooks.json";
import regionalJson from "./regional.json";
import reviewersJson from "./reviewers.json";
import strategiesJson from "./strategies.json";
import trustJson from "./trust.json";

const dataModeLabels = {
  project: "PROJECT",
  hybrid: "HYBRID",
  demo: "DEMO",
};

export const operationsSummary = {
  ...operationsJson,
  dataModeLabel:
    dataModeLabels[operationsJson.dataMode] ??
    String(operationsJson.dataMode).toUpperCase(),
};

export const reviewers = reviewersJson;

export const trustData = trustJson;

export const playbooks = playbooksJson;

export const regionalRisk = regionalJson;

export const riskTypes = [
  ...new Set(reviewersJson.map((reviewer) => reviewer.riskType)),
];

// Per-reviewer detail is far larger than the worklist rows, so it is served
// from public/ and fetched the first time a Reviewer 360 screen opens rather
// than bundled. Behaves like the GET /reviewers/:id call that will replace it.
let detailPromise = null;

export function loadReviewerDetails() {
  if (!detailPromise) {
    detailPromise = fetch("/data/reviewer-details.json").then((response) => {
      if (!response.ok) {
        throw new Error(`상세 데이터를 불러오지 못했습니다 (${response.status})`);
      }
      return response.json();
    });
  }

  return detailPromise;
}

// Mirrors core.insights.strategy_for: title/summary from the predicted state,
// secondary action and channel from the risk type.
export function strategyFor(predictedState, riskType) {
  const byState = strategiesJson.byState[String(predictedState)] ?? {
    title: "관찰 유지",
    description: "",
  };
  const byRiskType = strategiesJson.byRiskType[riskType] ?? {
    secondary: "",
    channel: "",
  };

  return { ...byState, ...byRiskType };
}

// Mirrors core.components.py's rank_badge: below 0.1%, a rounded ".0%" reads
// as "not even top-ranked" when the reviewer actually is. Streamlit floors
// the label at "0.1% 이내" instead of rounding to zero.
export function formatTopPercent(topPercent) {
  return topPercent < 0.1 ? "0.1% 이내" : `${topPercent.toFixed(1)}%`;
}
