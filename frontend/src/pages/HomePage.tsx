import { Activity } from "lucide-react";
import { useEffect } from "react";
import { checkBackendHealth } from "../app/store";
import { useAppDispatch, useAppSelector } from "../app/hooks";

function statusText(status: string) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function HomePage() {
  const dispatch = useAppDispatch();
  const { frontendStatus, backendStatus, databaseStatus } = useAppSelector(
    (state) => state.applicationStatus
  );

  useEffect(() => {
    void dispatch(checkBackendHealth());
  }, [dispatch]);

  return (
    <main className="home-shell">
      <section className="home-panel" aria-labelledby="product-title">
        <div className="status-icon" aria-hidden="true">
          <Activity size={28} strokeWidth={2.2} />
        </div>
        <h1 id="product-title">PharmaQ Sentinel</h1>
        <p className="subtitle">AI Pharmaceutical Complaint Intelligence</p>
        <div className="status-grid" aria-label="Application status">
          <p>Frontend status: {statusText(frontendStatus)}</p>
          <p>Backend API status: {statusText(backendStatus)}</p>
          <p>MySQL connection status: {statusText(databaseStatus)}</p>
        </div>
        <p className="ready-line">Application foundation ready</p>
      </section>
    </main>
  );
}
