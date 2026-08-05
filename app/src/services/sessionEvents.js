// Shared `window` event name for "a server call just got a 401 while the
// client still thinks it's logged in." Kept in its own module (rather than
// decisionService.js exporting it) so features/auth can listen for it
// without importing a specific data-service module — any service that talks
// to a session-protected API can dispatch it the same way.
export const SESSION_EXPIRED_EVENT = "auth:session-expired";
