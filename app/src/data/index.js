// Static v04 parity/reference data, exported from shared/retention by
// scripts/export_frontend_data.py. Regenerate after the model or profiles change:
//
//     ./.venv/Scripts/python.exe scripts/export_frontend_data.py
//
// Runtime screen data comes from FastAPI/MySQL. The static JSON files remain in
// the repository as parity-reference and recovery artifacts; API failures do
// not trigger an automatic JSON fallback.
import strategiesJson from "./strategies.json";

// 모든 운영 화면은 FastAPI 읽기 전용 서버(api/main.py)를 조회한다.
// docs/ui/REACT_V04_DB_INTEGRATION_PLAN.md 참고.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

// operationsSummary/reviewers/riskTypes는 여러 파일(Header 포함)에서
// 동기적으로 쓰여 화면별 비동기 로딩이 안 맞는다. OperationsContext와
// operations-context의 Provider/hooks로 옮겼다 — 여기서는 더 이상
// 내보내지 않는다.

// 리텐션 플레이북은 API에서 조회한다(api/routers/playbooks.py,
// retention_playbooks + retention_playbook_risk_actions).
let playbooksPromise = null;

export function loadPlaybooks() {
  if (!playbooksPromise) {
    playbooksPromise = fetch(`${API_BASE_URL}/api/playbooks`).then((response) => {
      if (!response.ok) {
        throw new Error(`플레이북 데이터를 불러오지 못했습니다 (${response.status})`);
      }
      return response.json();
    });
  }

  return playbooksPromise;
}

// Trust Center는 API에서 조회한다(api/routers/trust.py). v02/v03/v04
// 평가지표를 한 번에 묶어 반환하므로 regional과 같은 캐시된 promise 패턴.
let trustPromise = null;

export function loadTrustData() {
  if (!trustPromise) {
    trustPromise = fetch(`${API_BASE_URL}/api/trust`).then((response) => {
      if (!response.ok) {
        throw new Error(`Trust Center 데이터를 불러오지 못했습니다 (${response.status})`);
      }
      return response.json();
    });
  }

  return trustPromise;
}

// 콘텐츠 위험(권역) 화면은 API에서 조회한다(api/routers/regional.py,
// vw_regional_risk_summary). 다른 정적 JSON과 달리 비동기라 캐시된
// promise로 노출하고, 화면은 loadReviewerDetail()과 같은 방식으로 쓴다.
let regionalPromise = null;

export function loadRegionalRisk() {
  if (!regionalPromise) {
    regionalPromise = fetch(`${API_BASE_URL}/api/regional`).then((response) => {
      if (!response.ok) {
        throw new Error(`권역 데이터를 불러오지 못했습니다 (${response.status})`);
      }
      return response.json();
    });
  }

  return regionalPromise;
}

export function loadRegionalDerivedContext(selectionYear = 2018) {
  return fetch(
    `${API_BASE_URL}/api/regional/derived-context?selection_year=${selectionYear}`,
  ).then((response) => {
    if (!response.ok) {
      throw new Error(`권역 파생 데이터를 불러오지 못했습니다 (${response.status})`);
    }
    return response.json();
  });
}

const recommendationPromises = new Map();

export function loadReviewerRecommendations(userId) {
  if (!recommendationPromises.has(userId)) {
    recommendationPromises.set(
      userId,
      fetch(
        `${API_BASE_URL}/api/reviewer-details/${encodeURIComponent(userId)}/recommendations`,
      ).then((response) => {
        if (!response.ok) {
          throw new Error(`추천 음식점을 불러오지 못했습니다 (${response.status})`);
        }
        return response.json();
      }),
    );
  }
  return recommendationPromises.get(userId);
}

// Per-reviewer detail is far larger than the worklist rows, so each reviewer
// is fetched individually (api/routers/reviewer_details.py,
// vw_reviewer_validation) the first time their Reviewer 360 screen opens,
// not as one bulk payload for all reviewers (H-1).
const detailPromises = new Map();

// Resolved alongside each promise so pages that remount on reviewerId change
// (ReviewerDetailPage is keyed by it) can read a synchronous snapshot as
// their useState initializer instead of always starting from null — that's
// what was causing the "불러오는 중" flash on every reviewer switch even
// though a given reviewer's detail is only ever fetched once (B-11).
const resolvedDetails = new Map();

export function loadReviewerDetail(userId) {
  if (!detailPromises.has(userId)) {
    detailPromises.set(
      userId,
      fetch(`${API_BASE_URL}/api/reviewer-details/${encodeURIComponent(userId)}`)
        .then((response) => {
          if (!response.ok) {
            throw new Error(`상세 데이터를 불러오지 못했습니다 (${response.status})`);
          }
          return response.json();
        })
        .then((detail) => {
          resolvedDetails.set(userId, detail);
          return detail;
        }),
    );
  }

  return detailPromises.get(userId);
}

// Synchronous best-effort read — null until loadReviewerDetail(userId) has
// resolved for this reviewer. Never triggers a fetch itself.
export function getCachedReviewerDetail(userId) {
  return resolvedDetails.get(userId) ?? null;
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
