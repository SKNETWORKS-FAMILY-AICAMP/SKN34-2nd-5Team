// Keyed by `${modelVersion}::${sampleId}`, mirroring Streamlit's
// model_version + sample_id composite key (docs/STREAMLIT_DATA_CONTRACT.md).
// This is a separate, browser-local store — it is never synced with
// Streamlit's server-side judgment file, and old v03 `userId`-only entries
// are not carried forward under the new key.
const STORAGE_KEY = "reviewer-retention-decisions";

function buildKey(modelVersion, sampleId) {
  return `${modelVersion}::${sampleId}`;
}

function readAll() {
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

function writeAll(decisions) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(decisions));
}

// { [sampleId]: decision } for one model version, so callers can look
// reviewers up by sampleId without repeating the model_version prefix.
export function getDecisionsForModel(modelVersion) {
  const prefix = buildKey(modelVersion, "");
  const scoped = {};

  Object.entries(readAll()).forEach(([key, value]) => {
    if (key.startsWith(prefix)) {
      scoped[key.slice(prefix.length)] = value;
    }
  });

  return scoped;
}

export function getDecision(modelVersion, sampleId) {
  return readAll()[buildKey(modelVersion, sampleId)] ?? null;
}

export function saveDecision(modelVersion, sampleId, decision) {
  const nextDecisions = {
    ...readAll(),
    [buildKey(modelVersion, sampleId)]: decision,
  };

  writeAll(nextDecisions);

  return nextDecisions;
}

export function removeDecision(modelVersion, sampleId) {
  const nextDecisions = { ...readAll() };

  delete nextDecisions[buildKey(modelVersion, sampleId)];

  writeAll(nextDecisions);

  return nextDecisions;
}