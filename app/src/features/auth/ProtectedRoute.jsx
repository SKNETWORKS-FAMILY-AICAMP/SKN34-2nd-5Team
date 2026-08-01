import { useEffect } from "react";

import { useAuth } from "./auth-context";

// The session lives in auth_service, a separate FastAPI app served under
// /auth — not in this React router. So "not authenticated" means a full
// browser navigation to /auth/login (the Jinja login page), not a
// client-side <Navigate>. That navigation is a side effect, so it has to
// run from an effect rather than during render.
function ProtectedRoute({ children }) {
  const { status } = useAuth();

  useEffect(() => {
    if (status === "unauthenticated") {
      window.location.href = "/auth/login";
    }
  }, [status]);

  if (status === "loading" || status === "unauthenticated") {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-[#626D67]">
        로그인 상태를 확인하는 중…
      </div>
    );
  }

  return children;
}

export default ProtectedRoute;
