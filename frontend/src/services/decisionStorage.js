const STORAGE_KEY = "reviewer-retention-decisions";

export function getDecisions() {
  try {
    const savedValue = window.localStorage.getItem(STORAGE_KEY);

    if (!savedValue) {
      return {};
    }

    const parsedValue = JSON.parse(savedValue);

    return typeof parsedValue === "object" && parsedValue !== null
      ? parsedValue
      : {};
  } catch {
    return {};
  }
}

export function getDecision(reviewerId) {
  const decisions = getDecisions();

  return decisions[reviewerId] ?? null;
}

export function saveDecision(reviewerId, decision) {
  const decisions = getDecisions();

  const nextDecisions = {
    ...decisions,
    [reviewerId]: decision,
  };

  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(nextDecisions),
  );

  return nextDecisions;
}

export function removeDecision(reviewerId) {
  const decisions = getDecisions();
  const nextDecisions = { ...decisions };

  delete nextDecisions[reviewerId];

  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(nextDecisions),
  );

  return nextDecisions;
}