import { Route, Routes } from "react-router-dom";
import { ComplaintWorkspacePage } from "./pages/ComplaintWorkspacePage";
import { QmsLedgerPage } from "./pages/QmsLedgerPage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<ComplaintWorkspacePage />} />
      <Route path="/qms-ledger" element={<QmsLedgerPage />} />
    </Routes>
  );
}
