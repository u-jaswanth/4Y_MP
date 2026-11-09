import { useEffect, useState } from "react";

import AppNav from "../components/AppNav";
import ReceiptVerifier from "../components/ReceiptVerifier";

import {
  getAccessRequests,
  approveAccessRequest,
  denyAccessRequest,
  revokeAccess,
  getConsentHistory,
} from "../services/portalApi";

/**
 * DoctorAccess
 * ------------------------------------------------------------
 * The patient's side of the doctor-access flow (see mockup.html,
 * "p-access"). A doctor who has the patient's Health ID can only ever
 * send a REQUEST - this page is the only place that request turns
 * into actual access, and the only place it can be taken away again.
 *
 * Two lists, same as the mock-up:
 *   - Pending requests  -> Approve / Deny
 *   - Active access     -> Revoke
 *
 * A third card, "Consent history", lists every request - including
 * denied and revoked ones that the two lists above no longer show -
 * with each step as recorded in the tamper-evident consent ledger, a
 * short receipt code the patient can copy and keep, a badge showing
 * whether the step is covered by a blockchain anchor, and a "Verify"
 * panel that re-checks the proof on the patient's own device.
 *
 * Nothing here is destructive by surprise: approving is one click
 * (the doctor already explained why, in their note), but revoking
 * asks for a confirmation, the same way removing a hospital's doctor
 * does on the hospital portal.
 */

function DoctorAccess() {

  const [pending, setPending] = useState([]);
  const [active, setActive] = useState([]);

  const [history, setHistory] = useState([]);
  const [historyError, setHistoryError] = useState("");

  // Which receipt code was just copied, so its button can say so.
  const [copiedHash, setCopiedHash] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Track in-flight actions per request id so only that row's buttons
  // disable, not the whole list.
  const [busyId, setBusyId] = useState(null);


  // ==========================================
  // LOAD
  // ==========================================

  async function load() {

    try {

      setError("");

      const data = await getAccessRequests();

      setPending(data.pending || []);
      setActive(data.active || []);

    } catch (loadError) {

      setError(
        loadError.message ||
        "Could not load your doctor access requests."
      );

    } finally {

      setLoading(false);

    }

    // Separate from the lists above: if the history can't load, the
    // approve / deny / revoke controls should still work.
    try {

      setHistoryError("");

      setHistory(await getConsentHistory());

    } catch (historyLoadError) {

      setHistoryError(
        historyLoadError.message ||
        "Could not load your consent history."
      );

    }
  }

  useEffect(() => {
    load();
  }, []);


  // ==========================================
  // ACTIONS
  // ==========================================

  async function handleApprove(request) {

    setError("");
    setMessage("");
    setBusyId(request.id);

    try {

      await approveAccessRequest(request.id);

      setMessage(
        `${doctorLabel(request)} can now see your reports and summary.`
      );

      await load();

    } catch (actionError) {

      setError(actionError.message);

    } finally {

      setBusyId(null);

    }
  }


  async function handleDeny(request) {

    setError("");
    setMessage("");
    setBusyId(request.id);

    try {

      await denyAccessRequest(request.id);

      setMessage(`Request from ${doctorLabel(request)} denied.`);

      await load();

    } catch (actionError) {

      setError(actionError.message);

    } finally {

      setBusyId(null);

    }
  }


  async function handleRevoke(request) {

    const ok = window.confirm(
      `Revoke ${doctorLabel(request)}'s access to your reports? ` +
      "They will need to send a new request to see them again."
    );

    if (!ok) {
      return;
    }

    setError("");
    setMessage("");
    setBusyId(request.id);

    try {

      await revokeAccess(request.id);

      setMessage(`Access for ${doctorLabel(request)} revoked.`);

      await load();

    } catch (actionError) {

      setError(actionError.message);

    } finally {

      setBusyId(null);

    }
  }


  // ==========================================
  // HELPERS
  // ==========================================

  function doctorLabel(request) {

    const doctor = request.doctor;

    if (!doctor) {
      return "This doctor";
    }

    return doctor.full_name;
  }


  const EVENT_LABELS = {
    requested: "Doctor requested access",
    approved: "You approved",
    denied: "You denied",
    revoked: "You revoked access",
  };

  const STATUS_PILLS = {
    pending: { text: "Pending", className: "pill-warn" },
    approved: { text: "Approved", className: "pill-ok" },
    denied: { text: "Denied", className: "pill-muted" },
    revoked: { text: "Revoked", className: "pill-muted" },
  };

  // How a step's blockchain anchor is shown. `anchor` is absent until
  // the next scheduled anchor covers the step. "local" is a test mode
  // that writes to the server's own disk, so it is labelled honestly
  // rather than shown as a blockchain.
  function anchorBadge(anchor) {

    if (!anchor) {
      return { text: "Not on blockchain yet", className: "pill-muted" };
    }

    if (anchor.provider === "local") {
      return { text: "Test anchor", className: "pill-muted" };
    }

    if (anchor.status === "confirmed") {
      return { text: "On blockchain", className: "pill-ok" };
    }

    return { text: "Anchoring…", className: "pill-warn" };
  }


  function formatDateTime(value) {

    if (!value) {
      return "";
    }

    // The server stores UTC without a zone marker; add one so the
    // browser shows the patient's own local time.
    // Trim microseconds to milliseconds too: Safari rejects 6-digit
    // fractions that Chrome and Firefox accept.
    const trimmed = value.replace(/(\.\d{3})\d+/, "$1");

    const iso = /Z|[+-]\d\d:?\d\d$/.test(trimmed) ? trimmed : `${trimmed}Z`;

    return new Date(iso).toLocaleString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }


  async function copyReceipt(hash) {

    try {

      await navigator.clipboard.writeText(hash);

      setCopiedHash(hash);

      setTimeout(() => setCopiedHash(null), 1800);

    } catch {

      // Clipboard can be blocked (http, old browser). The full code is
      // in the button's tooltip, so it can still be selected by hand.
      setCopiedHash(null);

    }
  }


  function formatDate(value) {

    if (!value) {
      return null;
    }

    return new Date(value).toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  }


  // ==========================================
  // RENDER
  // ==========================================

  if (loading) {

    return (

      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <p>Loading doctor access…</p>
      </div>

    );
  }

  return (

    <div className="dashboard-page">

      <AppNav active="access" />

      <main className="dashboard-content">

        <div className="dashboard-header">

          <div>
            <h1>Doctor access</h1>
            <p>
              A doctor can only see your reports and summary once you
              approve their request here - and you can take it away
              again at any time.
            </p>
          </div>

        </div>

        {error && <div className="error-message">{error}</div>}
        {message && <div className="success-message">{message}</div>}


        {/* ====================================
            PENDING REQUESTS
        ==================================== */}

        <div className="dashboard-card">

          <h3 className="form-section-title">
            Pending request{pending.length === 1 ? "" : "s"}
          </h3>

          {pending.length === 0 ? (

            <p className="portal-note">
              No one is currently waiting on a decision from you.
            </p>

          ) : (

            <div className="entity-list">

              {pending.map((request) => (

                <div className="entity-card" key={request.id}>

                  <div className="entity-main">

                    <div className="entity-title-row">

                      <h3>{doctorLabel(request)}</h3>

                      {request.doctor?.specialty && (
                        <span className="pill pill-specialty">
                          {request.doctor.specialty}
                        </span>
                      )}

                    </div>

                    <p className="entity-sub">
                      {request.doctor?.hospital
                        ? `Requesting record access · ${request.doctor.hospital}`
                        : "Requesting access to your reports and summary"}
                    </p>

                    {request.note && (
                      <p className="entity-focus">"{request.note}"</p>
                    )}

                  </div>

                  <div className="entity-actions">

                    <button
                      className="secondary-btn"
                      disabled={busyId === request.id}
                      onClick={() => handleDeny(request)}
                    >
                      Deny
                    </button>

                    <button
                      className="primary-btn compact-btn"
                      disabled={busyId === request.id}
                      onClick={() => handleApprove(request)}
                    >
                      {busyId === request.id ? "Working…" : "Approve"}
                    </button>

                  </div>

                </div>

              ))}

            </div>

          )}

        </div>


        {/* ====================================
            ACTIVE ACCESS
        ==================================== */}

        <div className="dashboard-card">

          <h3 className="form-section-title">Active access</h3>

          {active.length === 0 ? (

            <p className="portal-note">
              No doctor currently has access to your reports.
            </p>

          ) : (

            <div className="entity-list">

              {active.map((request) => (

                <div className="entity-card" key={request.id}>

                  <div className="entity-main">

                    <div className="entity-title-row">

                      <h3>{doctorLabel(request)}</h3>

                      {request.doctor?.specialty && (
                        <span className="pill pill-specialty">
                          {request.doctor.specialty}
                        </span>
                      )}

                      <span className="pill pill-ok">Approved</span>

                    </div>

                    <p className="entity-sub">
                      {[
                        request.doctor?.hospital,
                        request.decided_at
                          ? `Approved ${formatDate(request.decided_at)}`
                          : null,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>

                  </div>

                  <div className="entity-actions">

                    <button
                      className="link-btn danger-link"
                      disabled={busyId === request.id}
                      onClick={() => handleRevoke(request)}
                    >
                      {busyId === request.id ? "Working…" : "Revoke"}
                    </button>

                  </div>

                </div>

              ))}

            </div>

          )}

        </div>


        {/* ====================================
            CONSENT HISTORY (from the ledger)
        ==================================== */}

        <div className="dashboard-card">

          <h3 className="form-section-title">Consent history</h3>

          <p className="portal-note">
            Every request and decision is written to a tamper-evident
            log, and that log is regularly fingerprinted on a public
            blockchain so it cannot be quietly rewritten later. Each
            step gets a receipt code - keep it if you ever need to show
            what you decided, and when. Use Verify to check a step.
          </p>

          {historyError && (
            <div className="error-message">{historyError}</div>
          )}

          {!historyError && history.length === 0 ? (

            <p className="portal-note">
              Nothing here yet. Requests and your decisions will appear
              as soon as a doctor asks for access.
            </p>

          ) : (

            <div className="history-list">

              {history.map((item) => {

                const pill = STATUS_PILLS[item.status];

                return (

                  <details className="history-item" key={item.request_id}>

                    <summary className="history-summary">

                      <span className="history-who">
                        <strong>
                          {item.doctor?.full_name || "This doctor"}
                        </strong>

                        {item.doctor?.hospital && (
                          <span className="entity-sub">
                            {item.doctor.hospital}
                          </span>
                        )}
                      </span>

                      {pill && (
                        <span className={`pill ${pill.className}`}>
                          {pill.text}
                        </span>
                      )}

                      <span className="entity-sub history-count">
                        {item.events.length === 0
                          ? "No receipts"
                          : `${item.events.length} step${
                              item.events.length === 1 ? "" : "s"
                            }`}
                      </span>

                    </summary>

                    {item.events.length === 0 ? (

                      <p className="portal-note history-empty">
                        This request was made before the log was
                        introduced, so it has no receipts.
                      </p>

                    ) : (

                      <ol className="history-steps">

                        {item.events.map((event) => (

                          <li className="history-step" key={event.seq}>

                            <div className="history-step-row">

                              <span
                                className={`history-dot history-dot-${event.event_type}`}
                                aria-hidden="true"
                              ></span>

                              <div className="history-step-body">

                                <span className="history-step-title">
                                  {EVENT_LABELS[event.event_type] ||
                                    event.event_type}
                                </span>

                                <span className="entity-sub">
                                  {formatDateTime(event.created_at)}
                                </span>

                              </div>

                              <span
                                className={`pill ${anchorBadge(event.anchor).className}`}
                              >
                                {anchorBadge(event.anchor).text}
                              </span>

                              <button
                                type="button"
                                className="link-btn history-receipt"
                                title={event.event_hash}
                                onClick={() => copyReceipt(event.event_hash)}
                              >
                                {copiedHash === event.event_hash
                                  ? "Copied"
                                  : `Receipt ${event.event_hash.slice(0, 8)}`}
                              </button>

                            </div>

                            <ReceiptVerifier eventHash={event.event_hash} />

                          </li>

                        ))}

                      </ol>

                    )}

                  </details>

                );

              })}

            </div>

          )}

        </div>

      </main>

    </div>
  );
}

export default DoctorAccess;
