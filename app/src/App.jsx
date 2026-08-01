import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router";

import CommandPalette from "./components/common/CommandPalette";
import Header from "./components/Header";
import ScrollToTop from "./components/ScrollToTop";
import Skeleton from "./components/common/Skeleton";
import { OperationsGate, OperationsProvider } from "./context/OperationsContext";
import { DecisionGate, DecisionProvider } from "./context/DecisionContext";
import { AuthProvider } from "./features/auth/AuthProvider";
import ProtectedRoute from "./features/auth/ProtectedRoute";

// Route-level code splitting (H-1 adjacent QA item): recharts is only
// pulled into the Trust Center and Reviewer 360 chunks, not the initial
// bundle every screen used to share.
const OperationsPage = lazy(() => import("./pages/OperationsPage"));
const PlaybookPage = lazy(() => import("./pages/PlaybookPage"));
const RegionalRiskPage = lazy(() => import("./pages/RegionalRiskPage"));
const ReviewerListPage = lazy(() => import("./pages/ReviewerListPage"));
const TrustCenterPage = lazy(() => import("./pages/TrustCenterPage"));
const ReviewerDetailPage = lazy(() => import("./pages/ReviewerDetailPage"));

function App() {
  return (
    <AuthProvider>
      <ProtectedRoute>
        <OperationsProvider>
          <OperationsGate>
            <DecisionProvider>
              <DecisionGate>
                <div className="min-h-screen bg-[#F7F8F5] text-[#17211D]">
                  <ScrollToTop />
                  <Header />
                  <CommandPalette />

                  <main className="mx-auto max-w-[1540px] px-6 py-10">
                    <Suspense fallback={<Skeleton rows={6} columns={4} />}>
                      <Routes>
                        <Route path="/" element={<OperationsPage />} />
                        <Route path="/reviewers" element={<ReviewerListPage />} />

                        <Route
                          path="/reviewers/:reviewerId"
                          element={<ReviewerDetailPage />}
                        />

                        <Route path="/playbook" element={<PlaybookPage />} />
                        <Route path="/regional" element={<RegionalRiskPage />} />
                        <Route path="/trust" element={<TrustCenterPage />} />
                      </Routes>
                    </Suspense>
                  </main>
                </div>
              </DecisionGate>
            </DecisionProvider>
          </OperationsGate>
        </OperationsProvider>
      </ProtectedRoute>
    </AuthProvider>
  );
}

export default App;
