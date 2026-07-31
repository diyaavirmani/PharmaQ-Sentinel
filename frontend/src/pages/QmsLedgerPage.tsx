import { FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useGetComplaintsQuery } from "../features/complaint/complaintApi";
import type { ComplaintResponse } from "../features/complaint/complaintTypes";
import "../styles/workspace.css";

function display(value: string | null | undefined) {
  return value && value.trim() ? value : "Not provided";
}

function formatDate(value: string | null | undefined) {
  if (!value) {
    return "Not provided";
  }
  return value.slice(0, 10);
}

function LedgerRow({ complaint }: { complaint: ComplaintResponse }) {
  return (
    <tr>
      <td>{complaint.complaint_number}</td>
      <td>{display(complaint.product_name)}</td>
      <td>{display(complaint.batch_lot_number)}</td>
      <td>{display(complaint.customer_name)}</td>
      <td>{display(complaint.complaint_type)}</td>
      <td>{display(complaint.suggested_severity)}</td>
      <td>{display(complaint.status)}</td>
      <td>{formatDate(complaint.complaint_date)}</td>
      <td>{formatDate(complaint.committed_at)}</td>
    </tr>
  );
}

export function QmsLedgerPage() {
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 10;
  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    if (search.trim()) {
      params.set("product_name", search.trim());
    }
    if (severity) {
      params.set("severity", severity);
    }
    if (status) {
      params.set("status", status);
    }
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    return params.toString();
  }, [offset, search, severity, status]);
  const { data, isFetching, isError, refetch } = useGetComplaintsQuery(queryString);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOffset(0);
  }

  return (
    <main className="workspace-page" aria-label="PharmaQ Sentinel QMS ledger" data-font-family="Inter">
      <section className="qms-ledger">
        <header className="qms-ledger__header">
          <div>
            <p>Demonstration QMS Ledger</p>
            <h1>Saved Complaints</h1>
          </div>
          <Link className="button button--secondary" to="/">
            Complaint Workspace
          </Link>
        </header>

        <form className="qms-ledger__filters" onSubmit={handleSubmit}>
          <label>
            Search
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Product name"
            />
          </label>
          <label>
            Severity
            <select value={severity} onChange={(event) => setSeverity(event.target.value)}>
              <option value="">All</option>
              <option value="CRITICAL">Critical</option>
              <option value="MAJOR">Major</option>
              <option value="MINOR">Minor</option>
              <option value="UNDETERMINED">Undetermined</option>
            </select>
          </label>
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">All</option>
              <option value="COMMITTED">Committed</option>
              <option value="CLOSED">Closed</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </label>
          <button type="submit" className="button button--primary">
            Search
          </button>
        </form>

        {isFetching ? <div className="qms-ledger__state">Loading saved complaints...</div> : null}
        {isError ? (
          <div className="qms-ledger__state qms-ledger__state--error" role="alert">
            Could not load the QMS ledger.
            <button type="button" className="button button--secondary" onClick={() => refetch()}>
              Retry
            </button>
          </div>
        ) : null}

        {!isFetching && !isError && data?.items.length === 0 ? (
          <div className="qms-ledger__state">No saved complaint records match these filters.</div>
        ) : null}

        {data?.items.length ? (
          <div className="qms-ledger__table-wrap">
            <table className="qms-ledger__table">
              <thead>
                <tr>
                  <th>Complaint Number</th>
                  <th>Product</th>
                  <th>Batch</th>
                  <th>Customer</th>
                  <th>Complaint Type</th>
                  <th>Suggested Severity</th>
                  <th>Status</th>
                  <th>Complaint Date</th>
                  <th>Saved Date</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((complaint) => (
                  <LedgerRow complaint={complaint} key={complaint.id} />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        <footer className="qms-ledger__pagination">
          <button
            type="button"
            className="button button--secondary"
            disabled={offset === 0}
            onClick={() => setOffset(Math.max(0, offset - limit))}
          >
            Previous
          </button>
          <span>Page {Math.floor(offset / limit) + 1}</span>
          <button
            type="button"
            className="button button--secondary"
            disabled={!data?.next_offset}
            onClick={() => setOffset(data?.next_offset ?? offset)}
          >
            Next
          </button>
        </footer>
      </section>
    </main>
  );
}
