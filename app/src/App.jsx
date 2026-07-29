import { Route, Routes } from "react-router";

import Header from "./components/Header";
import ScrollToTop from "./components/ScrollToTop";
import { OperationsGate, OperationsProvider } from "./context/OperationsContext";
import OperationsPage from "./pages/OperationsPage";
import PlaybookPage from "./pages/PlaybookPage";
import RegionalRiskPage from "./pages/RegionalRiskPage";
import ReviewerListPage from "./pages/ReviewerListPage";
import TrustCenterPage from "./pages/TrustCenterPage";
import ReviewerDetailPage from "./pages/ReviewerDetailPage";

function App() {
  return (
    <OperationsProvider>
      <OperationsGate>
        <div className="min-h-screen bg-[#F7F8F5] text-[#17211D]">
          <ScrollToTop />
          <Header />

          <main className="mx-auto max-w-[1540px] px-6 py-10">
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
          </main>
        </div>
      </OperationsGate>
    </OperationsProvider>
  );
}

export default App;