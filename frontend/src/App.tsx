import { Route, Routes } from "react-router-dom";
import { ComplaintWorkspacePage } from "./pages/ComplaintWorkspacePage";
import { LandingPage } from "./pages/LandingPage";
import { QmsLedgerPage } from "./pages/QmsLedgerPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/workspace" element={<ComplaintWorkspacePage />} />
      <Route path="/qms-ledger" element={<QmsLedgerPage />} />
    </Routes>
  );
}
