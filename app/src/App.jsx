import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router";

import CommandPalette from "./components/common/CommandPalette";
import AppShell from "./components/layout/AppShell";
import ScrollToTop from "./components/ScrollToTop";
import Skeleton from "./components/common/Skeleton";
import { OperationsGate, OperationsProvider } from "./context/OperationsContext";
import { DecisionGate, DecisionProvider } from "./context/DecisionContext";
import { AuthProvider } from "./features/auth/AuthProvider";
import ProtectedRoute from "./features/auth/ProtectedRoute";

// Route-level code splitting (H-1 adjacent QA item): recharts is only
// pulled into the Trust Center and Reviewer 360 chunks, not the initial
// bundle every screen used to share.
const HomePage = lazy(() => import("./pages/HomePage"));
const PlaybookPage = lazy(() => import("./pages/PlaybookPage"));
const ReviewerListPage = lazy(() => import("./pages/ReviewerListPage"));
const TrustCenterPage = lazy(() => import("./pages/TrustCenterPage"));
const ReviewerDetailPage = lazy(() => import("./pages/ReviewerDetailPage"));
const ContentNetworkPage = lazy(() => import("./pages/ContentNetworkPage"));
const OperationsHistoryPage = lazy(() => import("./pages/OperationsHistoryPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const SponsorshipManagementPage = lazy(() => import("./pages/SponsorshipManagementPage"));

function App() {
  return (
    <AuthProvider>
      <ProtectedRoute>
        <OperationsProvider>
          <OperationsGate>
            <DecisionProvider>
              <DecisionGate>
                <AppShell>
                  <ScrollToTop />
                  <CommandPalette />
                  <Suspense fallback={<Skeleton rows={6} columns={4} />}>
                    <Routes>
                      <Route path="/" element={<HomePage />} />
                      <Route path="/regional/home" element={<Navigate to="/" replace />} />
                      <Route path="/individual/home" element={<Navigate to="/reviewers?mode=individual&status=미검토&sort=우선순위" replace />} />
                      <Route path="/reviewers" element={<ReviewerListPage />} />
                      <Route path="/reviewers/:reviewerId" element={<ReviewerDetailPage />} />
                      <Route path="/playbook" element={<PlaybookPage />} />
                      <Route path="/regional" element={<Navigate to="/" replace />} />
                      <Route path="/content-network" element={<ContentNetworkPage />} />
                      <Route path="/operations-history" element={<OperationsHistoryPage />} />
                      <Route path="/trust" element={<TrustCenterPage />} />
                      <Route path="/settings" element={<SettingsPage />} />
                      <Route path="/settings/sponsorships" element={<SponsorshipManagementPage />} />
                    </Routes>
                  </Suspense>
                </AppShell>
              </DecisionGate>
            </DecisionProvider>
          </OperationsGate>
        </OperationsProvider>
      </ProtectedRoute>
    </AuthProvider>
  );
}

export default App;
