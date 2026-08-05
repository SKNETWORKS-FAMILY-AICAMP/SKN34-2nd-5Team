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
    let message = `스폰서 매장 정보를 처리하지 못했습니다 (${response.status})`;
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

export function loadSponsorships() {
  return request("/api/sponsorships");
}

export function searchSponsorshipBusinesses(query) {
  return request(`/api/sponsorships/businesses?q=${encodeURIComponent(query)}`);
}

export function createSponsorship(payload) {
  return request("/api/sponsorships", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateSponsorshipSchedule(sponsorshipId, payload) {
  return request(`/api/sponsorships/${encodeURIComponent(sponsorshipId)}/schedule`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function cancelSponsorshipRegistration(sponsorshipId) {
  return request(`/api/sponsorships/${encodeURIComponent(sponsorshipId)}/cancel`, {
    method: "POST",
  });
}

export function updateSponsorshipStatus(sponsorshipId, status) {
  return request(`/api/sponsorships/${encodeURIComponent(sponsorshipId)}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function reactivateSponsorship(sponsorshipId) {
  return request(`/api/sponsorships/${encodeURIComponent(sponsorshipId)}/reactivate`, {
    method: "POST",
  });
}
