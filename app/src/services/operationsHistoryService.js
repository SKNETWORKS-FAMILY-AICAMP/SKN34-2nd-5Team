const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function loadOperationsHistory() {
  const response = await fetch(`${API_BASE_URL}/api/retention/operations-history`, { credentials: "include" });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? `운영 이력을 불러오지 못했습니다. (${response.status})`);
  return body;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? `운영 알림을 처리하지 못했습니다. (${response.status})`);
  return body;
}

export function loadReviewAlertHistory(alertId) {
  return request(`/api/retention/review-alerts/${encodeURIComponent(alertId)}/history`);
}

export function resolveReviewAlert(alertId, payload) {
  return request(`/api/retention/review-alerts/${encodeURIComponent(alertId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
