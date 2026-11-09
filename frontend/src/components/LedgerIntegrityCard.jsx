import { useEffect, useState } from "react";

import {
  getLedgerStatus,
  verifyLedger,
  anchorLedgerNow,
} from "../services/portalApi";
import { formatDateTime } from "../services/dates";

/**
 * LedgerIntegrityCard
 * ------------------------------------------------------------
 * The admin's view of the consent ledger: did the last scheduled check
 * find anything, what is anchored on the blockchain, and buttons to
 * check or anchor right now.
 *
 * "Healthy" only ever means "no evidence of tampering was found". A
 * chain that could not be reached shows up under "Could not check", not
 * as a problem - those are different things and the card keeps them
 * apart.
 */

// The scheduled check and the live check return slightly different
// shapes; flatten both into one.
function fromLastCheck(last) {

  if (!last) {
    return null;
  }

  const d = last.details || {};

  const problems = [];

  if (d.chain && !d.chain.ok) {
    problems.push(
      `Event ${d.chain.broken_at_seq} fails the chain check: ${d.chain.reason}`
    );
  }

  if (d.mismatched?.length) {
    problems.push(
      `${d.mismatched.length} request(s) have a status that disagrees with the ledger`
    );
  }

  if (d.orphaned?.length) {
    problems.push(
      `${d.orphaned.length} ledger event(s) belong to requests that no longer exist`
    );
  }

  problems.push(...(d.anchor_problems || []));

  return {
    healthy: last.healthy,
    ranAt: last.ran_at,
    problems,
    unverified: d.unverified || [],
    warnings: d.warnings || [],
    unanchored: d.unanchored_events ?? 0,
    live: false,
  };
}


function fromReport(report) {

  const problems = [];

  if (!report.chain.ok) {
    problems.push(
      `Event ${report.chain.broken_at_seq} fails the chain check: ${report.chain.reason}`
    );
  }

  if (report.reconciliation.mismatched.length) {
    problems.push(
      `${report.reconciliation.mismatched.length} request(s) have a status that disagrees with the ledger`
    );
  }

  if (report.reconciliation.orphaned.length) {
    problems.push(
      `${report.reconciliation.orphaned.length} ledger event(s) belong to requests that no longer exist`
    );
  }

  problems.push(...report.anchors.problems);

  return {
    healthy: report.healthy,
    ranAt: report.checked_at,
    problems,
    unverified: report.anchors.unverified,
    warnings: report.warnings,
    unanchored: report.anchors.unanchored_events,
    live: true,
  };
}


function LedgerIntegrityCard() {

  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");


  async function load() {

    try {

      setError("");

      const data = await getLedgerStatus();

      setStatus(data);
      setResult(fromLastCheck(data.last_check));

    } catch (loadError) {

      setError(loadError.message || "Could not load the ledger status.");

    } finally {

      setLoading(false);

    }
  }

  useEffect(() => {
    load();
  }, []);


  async function runCheck(full) {

    setBusy(full ? "full" : "check");
    setError("");
    setMessage("");

    try {

      setResult(fromReport(await verifyLedger(full)));

    } catch (checkError) {

      setError(checkError.message || "The check could not be run.");

    } finally {

      setBusy("");

    }
  }


  async function runAnchor() {

    setBusy("anchor");
    setError("");
    setMessage("");

    try {

      const data = await anchorLedgerNow();

      setMessage(
        data.published
          ? `Published an anchor covering ${data.anchor.event_count} event(s).`
          : data.detail
      );

      await load();

    } catch (anchorError) {

      setError(anchorError.message || "Could not publish an anchor.");

    } finally {

      setBusy("");

    }
  }


  const anchoring = status?.anchoring;

  let pill = { text: "No checks yet", className: "pill-muted" };

  if (result) {
    pill = result.healthy
      ? { text: "Healthy", className: "pill-ok" }
      : { text: "Problem found", className: "pill-alert" };
  }


  return (

    <div className="dashboard-card ledger-card">

      <div className="ledger-head">

        <h3 className="form-section-title">Consent ledger integrity</h3>

        {!loading && <span className={`pill ${pill.className}`}>{pill.text}</span>}

      </div>

      {loading && <p className="portal-note">Loading…</p>}

      {error && <div className="error-message">{error}</div>}
      {message && <div className="success-message">{message}</div>}

      {status && (

        <>

          <p className="portal-note">
            {result
              ? `${result.live ? "Checked just now" : "Last scheduled check"}: ${formatDateTime(result.ranAt)}. `
              : "The first scheduled check has not run yet. "}
            Checks run every {status.check_interval_minutes} minutes
            {status.worker_enabled ? "." : " - but the scheduler is switched off."}
          </p>

          {result?.problems.length > 0 && (
            <div className="error-message">
              <strong>Evidence of tampering or corruption:</strong>
              <ul className="ledger-list">
                {result.problems.map((p) => <li key={p}>{p}</li>)}
              </ul>
            </div>
          )}

          {result?.unverified.length > 0 && (
            <div className="ledger-notice">
              <strong>Could not check (not a sign of tampering):</strong>
              <ul className="ledger-list">
                {result.unverified.map((p) => <li key={p}>{p}</li>)}
              </ul>
            </div>
          )}

          {result?.warnings.length > 0 && (
            <div className="ledger-notice">
              <ul className="ledger-list">
                {result.warnings.map((p) => <li key={p}>{p}</li>)}
              </ul>
            </div>
          )}

          {result && (
            <p className="entity-sub">
              {result.unanchored} event{result.unanchored === 1 ? "" : "s"} waiting
              for the next anchor.
            </p>
          )}

          <h4 className="ledger-sub">Blockchain anchoring</h4>

          {!anchoring.enabled ? (

            <p className="portal-note">
              Switched off, so the ledger has no outside witness: someone
              with full database access could rewrite it undetected.
              {anchoring.configuration_problem &&
                ` Configuration problem: ${anchoring.configuration_problem}`}
            </p>

          ) : (

            <p className="portal-note">
              {anchoring.provider === "local"
                ? "Test mode - anchors are saved to a file on this server, not a blockchain. "
                : "Publishing to a public blockchain. "}
              A new anchor is published at most every {anchoring.interval_minutes} minutes.
              {anchoring.pinned_address && (
                <>
                  {" "}Anchors must come from{" "}
                  <code className="ledger-code">{anchoring.pinned_address}</code>.
                </>
              )}
            </p>

          )}

          {status.latest_anchors.length > 0 && (

            <div className="ledger-table-wrap">

              <table className="ledger-table">

                <thead>
                  <tr>
                    <th>Events</th>
                    <th>Status</th>
                    <th>Published</th>
                    <th>Transaction</th>
                  </tr>
                </thead>

                <tbody>

                  {status.latest_anchors.map((a) => (

                    <tr key={a.digest}>

                      <td>{a.from_seq}–{a.to_seq} ({a.event_count})</td>

                      <td>
                        <span
                          className={`pill ${a.status === "confirmed" ? "pill-ok" : "pill-warn"}`}
                        >
                          {a.status === "confirmed" ? "Confirmed" : "Pending"}
                        </span>
                      </td>

                      <td>{formatDateTime(a.published_at)}</td>

                      <td>
                        {a.explorer_url ? (
                          <a
                            className="link-btn"
                            href={a.explorer_url}
                            target="_blank"
                            rel="noreferrer noopener"
                          >
                            {a.tx_id.slice(0, 10)}… ↗
                          </a>
                        ) : (
                          <span className="entity-sub">
                            {a.tx_id ? `${a.tx_id.slice(0, 12)}…` : "-"}
                          </span>
                        )}
                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          )}

          <div className="ledger-actions">

            <button
              type="button"
              className="secondary-btn"
              disabled={busy !== ""}
              onClick={() => runCheck(false)}
            >
              {busy === "check" ? "Checking…" : "Check now"}
            </button>

            <button
              type="button"
              className="secondary-btn"
              disabled={busy !== "" || !anchoring.enabled}
              title="Asks the blockchain about every anchor, not just the newest"
              onClick={() => runCheck(true)}
            >
              {busy === "full" ? "Auditing…" : "Full audit"}
            </button>

            <button
              type="button"
              className="primary-btn compact-btn"
              disabled={busy !== "" || !anchoring.enabled}
              onClick={runAnchor}
            >
              {busy === "anchor" ? "Publishing…" : "Anchor now"}
            </button>

          </div>

        </>

      )}

    </div>
  );
}

export default LedgerIntegrityCard;
