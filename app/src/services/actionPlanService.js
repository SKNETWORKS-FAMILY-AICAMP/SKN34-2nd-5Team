const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: "include",
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.detail ?? `실행안을 처리하지 못했습니다. (${response.status})`);
  return body;
}

export function loadActionPlans(planType) {
  const query = planType ? `?plan_type=${encodeURIComponent(planType)}` : "";
  return request(`/api/retention/action-plans${query}`);
}

export function createActionPlan(payload) {
  return request("/api/retention/action-plans", { method: "POST", body: JSON.stringify(payload) });
}

export function updateActionPlan(planId, payload) {
  return request(`/api/retention/action-plans/${encodeURIComponent(planId)}`, { method: "PUT", body: JSON.stringify(payload) });
}
