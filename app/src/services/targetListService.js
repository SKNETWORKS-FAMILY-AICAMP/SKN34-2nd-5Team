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
    let message = `대상 명단을 처리하지 못했습니다 (${response.status})`;
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

export function loadTargetLists() {
  return request("/api/retention/target-lists");
}

export function createTargetList(payload) {
  return request("/api/retention/target-lists", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteTargetList(listId) {
  return request(`/api/retention/target-lists/${encodeURIComponent(listId)}`, {
    method: "DELETE",
  });
}
