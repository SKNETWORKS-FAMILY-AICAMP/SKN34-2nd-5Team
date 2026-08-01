// UX-level screen/action policy only — not a security boundary.
// REACT_INTEGRATION.md §8: "React에서 메뉴나 버튼을 숨기는 것은 사용자
// 경험 처리일 뿐 보안 경계가 아니다." Actual access control still has to
// happen server-side (Nginx /auth/api/verify subrequest or the analysis
// API itself) — tracked separately, not part of this pass.
export const ROLE_LABELS = {
  ADMIN: "관리자",
  OPERATOR: "운영자",
  VIEWER: "조회 전용",
};

// VIEWER can open every screen (all five are read-first views); they just
// shouldn't see controls that write data (판단 저장, 대상 명단 추가 등).
// Wiring this into each screen's buttons is a follow-up — this pass only
// adds the policy helper, not the per-button gating.
export function canMutate(accessRole) {
  return accessRole === "ADMIN" || accessRole === "OPERATOR";
}

export function roleLabel(accessRole) {
  return ROLE_LABELS[accessRole] ?? accessRole ?? "";
}
