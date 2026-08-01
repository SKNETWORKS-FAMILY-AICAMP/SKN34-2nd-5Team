const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `운영 데이터를 처리하지 못했습니다 (${response.status})`;
    try {
      const body = await response.json();
      if (body.detail) message = body.detail;
    } catch {
      // Keep the status-based message when the response is not JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

export function loadServerDecisions(modelVersion) {
  return request(
    `/api/retention/decisions?model_version=${encodeURIComponent(modelVersion)}`,
  );
}

export function saveServerDecision(reviewerUserId, payload) {
  return request(
    `/api/retention/decisions/${encodeURIComponent(reviewerUserId)}`,
    { method: "PUT", body: JSON.stringify(payload) },
  );
}

export function removeServerDecision(reviewerUserId) {
  return request(
    `/api/retention/decisions/${encodeURIComponent(reviewerUserId)}`,
    { method: "DELETE" },
  );
}

export function loadDecisionHistory(reviewerUserId) {
  return request(
    `/api/retention/decisions/${encodeURIComponent(reviewerUserId)}/history`,
  );
}

export function loadInteractions(reviewerUserId) {
  return request(
    `/api/retention/reviewers/${encodeURIComponent(reviewerUserId)}/interactions`,
  );
}

export function createInteraction(reviewerUserId, payload) {
  return request(
    `/api/retention/reviewers/${encodeURIComponent(reviewerUserId)}/interactions`,
    { method: "POST", body: JSON.stringify(payload) },
  );
}
