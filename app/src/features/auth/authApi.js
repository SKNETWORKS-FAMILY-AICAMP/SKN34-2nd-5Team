// Thin client for auth_service (see auth_service/REACT_INTEGRATION.md §6-7).
// Requests go through the Vite dev proxy (vite.config.js) or, in
// production, Nginx routing /auth to the same service — so this always
// calls a same-origin relative path, never a hardcoded host.
const AUTH_BASE = "/auth/api";

function getCsrfToken() {
  const cookie = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith("rr_auth_csrf="));
  return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
}

async function request(path, options = {}) {
  return fetch(`${AUTH_BASE}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
}

function errorMessage(body, fallbackStatus) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  return `요청을 처리하지 못했습니다 (${fallbackStatus})`;
}

export async function login(identifier, password) {
  const response = await request("/login", {
    method: "POST",
    body: JSON.stringify({ identifier, password }),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(errorMessage(body, response.status));
  }
  return body;
}

export async function logout() {
  const response = await request("/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": getCsrfToken() },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(errorMessage(body, response.status));
  }
}

// Returns null for "not logged in" (401/403) rather than throwing — that's
// an expected state on first load, not a failure. Anything else (network
// error, 5xx) throws so AuthProvider can surface a real problem.
export async function fetchCurrentUser() {
  const response = await request("/me");
  if (response.status === 401 || response.status === 403) {
    return null;
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(errorMessage(body, response.status));
  }
  return response.json();
}

export { getCsrfToken };
