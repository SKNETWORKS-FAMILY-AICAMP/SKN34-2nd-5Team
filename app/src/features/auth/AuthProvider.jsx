import { useEffect, useState } from "react";

import { AuthContext } from "./auth-context";
import {
  fetchCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
} from "./authApi";

// status: "loading" while /auth/api/me is in flight (see REACT_INTEGRATION.md
// §8 step "확인이 끝날 때까지 보호 화면을 먼저 렌더링하지 말고 로딩 상태를
// 둔다"), then "authenticated" or "unauthenticated".
export function AuthProvider({ children }) {
  const [state, setState] = useState({ status: "loading", user: null, error: null });
  // Bumping this re-runs the mount-check effect below — the same
  // "imperative refresh" shape DecisionContext would use if it needed one,
  // kept inline rather than as a separately called function (see
  // react-hooks/set-state-in-effect: calling a named async function from
  // inside an effect body is flagged, an inline fetch chain is not).
  const [refreshToken, setRefreshToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetchCurrentUser()
      .then((user) => {
        if (cancelled) return;
        setState({
          status: user ? "authenticated" : "unauthenticated",
          user,
          error: null,
        });
      })
      .catch((error) => {
        if (!cancelled) {
          setState({ status: "unauthenticated", user: null, error });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [refreshToken]);

  function refresh() {
    setRefreshToken((token) => token + 1);
  }

  async function login(identifier, password) {
    const result = await loginRequest(identifier, password);
    setState({ status: "authenticated", user: result.user, error: null });
    return result;
  }

  async function logout() {
    await logoutRequest();
    setState({ status: "unauthenticated", user: null, error: null });
    window.location.href = "/auth/login";
  }

  return (
    <AuthContext.Provider value={{ ...state, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}
