import { Route, Routes } from "react-router-dom";
import { ComplaintWorkspacePage } from "./pages/ComplaintWorkspacePage";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<ComplaintWorkspacePage />} />
    </Routes>
  );
}
