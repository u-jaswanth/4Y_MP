import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import PortalNav from "../components/PortalNav";
import RichText from "../components/RichText";

import { getDoctorProfile } from "../services/portalApi";
import { getReportFileUrl } from "../services/api";

import {
  lookupPatientForAccess,
  sendAccessRequest,
  getMyPatients,
  getPatientRecord,
  getPatientChatHistory,
  askAboutPatient,
} from "../services/portalApi";

/**
 * DoctorDashboard
 * ------------------------------------------------------------
 * Four things a logged-in doctor can do, as three tabs plus a record
 * view that opens on top of them (mirrors mockup.html's d-patients /
 * d-search / d-record views):
 *
 *   Find patient  - look a patient up by Health ID and send them an
 *                   access request, with a short note they'll see.
 *   My patients   - every patient who has approved a request, most
 *                   recently approved first.
 *   Your profile  - the doctor's own details (unchanged from before).
 *
 * Opening a patient from "My patients" shows their clinical summary,
 * an "Ask about this patient" chatbot scoped to their own analyzed
 * reports, and their report list - the same three things the patient
 * sees about themselves, read-only, and only for as long as access
 * stays approved.
 */

const REPORT_ICONS = {
  cbc: "🩸",
  blood: "🧪",
  lipid: "❤️",
  diabetes: "🩺",
  liver: "🫀",
  kidney: "🫘",
  thyroid: "🦋",
  urine: "🧪",
  vitamin: "💊",
  hormone: "🔬",
  imaging: "🩻",
  pathology: "🔬",
  cardiac: "❤️",
  other: "📋",
};


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


function DoctorDashboard() {

  const navigate = useNavigate();

  const [doctor, setDoctor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [tab, setTab] = useState("patients"); // "patients" | "find" | "profile"


  // ==========================================
  // MY PATIENTS
  // ==========================================

  const [myPatients, setMyPatients] = useState([]);
  const [loadingPatients, setLoadingPatients] = useState(false);
  const [patientsError, setPatientsError] = useState("");
  const [patientsLoaded, setPatientsLoaded] = useState(false);


  // ==========================================
  // FIND PATIENT
  // ==========================================

  const [healthIdInput, setHealthIdInput] = useState("");
  const [lookupResult, setLookupResult] = useState(null);
  const [lookupError, setLookupError] = useState("");
  const [lookingUp, setLookingUp] = useState(false);

  const [requestNote, setRequestNote] = useState("");
  const [sendingRequest, setSendingRequest] = useState(false);
  const [requestMessage, setRequestMessage] = useState("");


  // ==========================================
  // PATIENT RECORD (opened from My patients or
  // right after a lookup that's already approved)
  // ==========================================

  const [selectedPatientId, setSelectedPatientId] = useState(null);
  const [record, setRecord] = useState(null);
  const [loadingRecord, setLoadingRecord] = useState(false);
  const [recordError, setRecordError] = useState("");

  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatSending, setChatSending] = useState(false);
  const [chatError, setChatError] = useState("");

  const chatScrollRef = useRef(null);


  // ==========================================
  // LOAD DOCTOR PROFILE
  // ==========================================

  useEffect(() => {

    async function load() {

      try {

        setDoctor(await getDoctorProfile());

      } catch (error) {

        setError(error.message);

      } finally {

        setLoading(false);

      }
    }

    load();

  }, []);


  // ==========================================
  // LOAD MY PATIENTS (once, or when returning to the tab
  // after a record view closes / a new request is approved)
  // ==========================================

  async function loadMyPatients() {

    setLoadingPatients(true);
    setPatientsError("");

    try {

      const data = await getMyPatients();
      setMyPatients(data || []);
      setPatientsLoaded(true);

    } catch (error) {

      setPatientsError(error.message);

    } finally {

      setLoadingPatients(false);

    }
  }

  useEffect(() => {

    if (tab === "patients" && !patientsLoaded) {
      loadMyPatients();
    }

  }, [tab, patientsLoaded]);


  // ==========================================
  // AUTO-SCROLL THE CHAT
  // ==========================================

  useEffect(() => {

    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop =
        chatScrollRef.current.scrollHeight;
    }

  }, [chatMessages, chatSending]);


  // ==========================================
  // FIND PATIENT
  // ==========================================

  function resetLookup() {
    setHealthIdInput("");
    setLookupResult(null);
    setLookupError("");
    setRequestNote("");
    setRequestMessage("");
  }


  async function handleLookup(event) {

    event.preventDefault();

    setLookupError("");
    setLookupResult(null);
    setRequestMessage("");

    const cleaned = healthIdInput.replace(/\D/g, "");

    if (cleaned.length < 6) {
      setLookupError("Enter the full Health ID.");
      return;
    }

    setLookingUp(true);

    try {

      const patient = await lookupPatientForAccess(cleaned);
      setLookupResult(patient);

    } catch (error) {

      setLookupError(error.message);

    } finally {

      setLookingUp(false);

    }
  }


  async function handleSendRequest(event) {

    event.preventDefault();

    setLookupError("");
    setSendingRequest(true);

    try {

      await sendAccessRequest(lookupResult.health_id, requestNote.trim());

      setRequestMessage(
        `Request sent to ${lookupResult.full_name}. You'll get access ` +
        "as soon as they approve it."
      );

      setLookupResult((current) => ({ ...current, access_status: "pending" }));
      setRequestNote("");

    } catch (error) {

      setLookupError(error.message);

    } finally {

      setSendingRequest(false);

    }
  }


  // ==========================================
  // OPEN / CLOSE A PATIENT RECORD
  // ==========================================

  async function openPatientRecord(patientId) {

    setSelectedPatientId(patientId);
    setRecord(null);
    setRecordError("");
    setChatMessages([]);
    setChatError("");
    setLoadingRecord(true);

    try {

      const [recordData, historyData] = await Promise.all([
        getPatientRecord(patientId),
        getPatientChatHistory(patientId),
      ]);

      setRecord(recordData);
      setChatMessages(historyData.messages || []);

    } catch (error) {

      setRecordError(error.message);

    } finally {

      setLoadingRecord(false);

    }
  }


  function closeRecord() {
    setSelectedPatientId(null);
    setRecord(null);
    setRecordError("");
    setChatMessages([]);
    setChatInput("");
    setChatError("");
  }


  // ==========================================
  // "ASK ABOUT THIS PATIENT"
  // ==========================================

  async function handleAskAboutPatient(event) {

    event.preventDefault();

    const trimmed = chatInput.trim();

    if (!trimmed || chatSending) {
      return;
    }

    setChatError("");

    setChatMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setChatInput("");
    setChatSending(true);

    try {

      const data = await askAboutPatient(selectedPatientId, trimmed);

      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer },
      ]);

    } catch (error) {

      setChatError(error.message);

      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I couldn't process that question right now.",
        },
      ]);

    } finally {

      setChatSending(false);

    }
  }


  // ==========================================
  // RENDER: LOADING / ERROR
  // ==========================================

  if (loading) {

    return (

      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <p>Loading your profile…</p>
      </div>

    );
  }

  if (error) {

    return (

      <div className="portal-page">

        <PortalNav role="doctor" />

        <main className="portal-content">
          <div className="error-message">{error}</div>
        </main>

      </div>

    );
  }


  // ==========================================
  // RENDER: PATIENT RECORD VIEW
  // ==========================================

  if (selectedPatientId) {

    return (

      <div className="portal-page">

        <PortalNav role="doctor" subtitle={doctor.full_name} />

        <main className="portal-content portal-content-narrow">

          <div className="back-link" onClick={closeRecord}>
            ← My patients
          </div>

          {loadingRecord && (

            <div className="dashboard-loading">
              <div className="loading-spinner"></div>
              <p>Loading patient record…</p>
            </div>

          )}

          {!loadingRecord && recordError && (
            <div className="error-message">{recordError}</div>
          )}

          {!loadingRecord && record && (

            <>

              <div className="dashboard-header">

                <div>
                  <h1>{record.patient.full_name}</h1>
                  <p className="mono">{record.patient.health_id}</p>
                </div>

                <span className="pill pill-ok">Approved access</span>

              </div>


              {/* ====================================
                  CLINICAL SUMMARY
              ==================================== */}

              <div className="dashboard-card">

                <h3 className="form-section-title">Clinical summary</h3>

                <RichText>{record.clinical_summary}</RichText>

                <p className="field-hint">
                  {record.reports_analyzed > 0
                    ? `Built from ${record.reports_analyzed} processed ` +
                      `report${record.reports_analyzed === 1 ? "" : "s"}` +
                      (record.summary_generated_at
                        ? ` · updated ${formatDate(record.summary_generated_at)}`
                        : "")
                    : "This patient has no processed reports yet."}
                </p>

              </div>


              {/* ====================================
                  ASK ABOUT THIS PATIENT
              ==================================== */}

              <div className="dashboard-card chatbot-card">

                <h3 className="form-section-title">Ask about this patient</h3>

                <div className="chatbot-messages" ref={chatScrollRef}>

                  {chatMessages.length === 0 && (
                    <div className="chat-bubble chat-bubble-assistant">
                      Ask anything grounded in {record.patient.full_name}'s
                      analyzed reports - values, trends, or general
                      medical context around them.
                    </div>
                  )}

                  {chatMessages.map((message, index) => (

                    <div
                      key={index}
                      className={
                        message.role === "user"
                          ? "chat-bubble chat-bubble-user"
                          : "chat-bubble chat-bubble-assistant"
                      }
                    >
                      {message.role === "user" ? (
                        message.content
                      ) : (
                        <RichText>{message.content}</RichText>
                      )}
                    </div>

                  ))}

                  {chatSending && (
                    <div className="chat-bubble chat-bubble-assistant">
                      <span className="spinner"></span>
                    </div>
                  )}

                </div>

                {chatError && <div className="error-message">{chatError}</div>}

                <form
                  className="chatbot-input-row"
                  onSubmit={handleAskAboutPatient}
                >

                  <input
                    type="text"
                    value={chatInput}
                    onChange={(event) => setChatInput(event.target.value)}
                    placeholder="e.g. Any contraindications for a second agent alongside metformin?"
                    disabled={chatSending}
                  />

                  <button
                    className="primary-btn compact-btn"
                    type="submit"
                    disabled={chatSending || !chatInput.trim()}
                  >
                    Send
                  </button>

                </form>

              </div>


              {/* ====================================
                  REPORTS
              ==================================== */}

              <div className="dashboard-card">

                <h3 className="form-section-title">Reports</h3>

                {record.reports.length === 0 ? (

                  <p className="portal-note">
                    No reports uploaded yet.
                  </p>

                ) : (

                  <div className="entity-list">

                    {record.reports.map((report) => (

                      <div className="entity-card" key={report.id}>

                        <div className="entity-main">

                          <div className="entity-title-row">

                            <h3>
                              {REPORT_ICONS[report.report_type] || "📋"}{" "}
                              {report.report_name}
                            </h3>

                            {report.status === "summarized" ? (
                              <span className="pill pill-ok">Summarized</span>
                            ) : report.status === "failed" ? (
                              <span className="pill pill-warn">
                                Needs a retry
                              </span>
                            ) : (
                              <span className="pill pill-warn">
                                No results read
                              </span>
                            )}

                          </div>

                          <p className="entity-sub">
                            {formatDate(report.uploaded_at) || "Recently"}
                            {report.observation_count
                              ? ` · ${report.observation_count} results read`
                              : ""}
                          </p>

                        </div>

                        <div className="entity-actions">

                          <a
                            href={getReportFileUrl(report)}
                            target="_blank"
                            rel="noreferrer"
                            className="link-btn"
                          >
                            View PDF
                          </a>

                        </div>

                      </div>

                    ))}

                  </div>

                )}

              </div>

            </>

          )}

        </main>

      </div>

    );
  }


  // ==========================================
  // RENDER: TABS
  // ==========================================

  const listed = [
    doctor.specialty,
    doctor.qualification,
    doctor.experience_years
      ? `${doctor.experience_years} years in practice`
      : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (

    <div className="portal-page">

      <PortalNav
        role="doctor"
        subtitle={doctor.full_name}
        active={tab}
        onSelect={setTab}
        items={[
          { key: "patients", label: `My patients (${myPatients.length})`, icon: "users" },
          { key: "find", label: "Find patient", icon: "search" },
          { key: "profile", label: "Your profile", icon: "user" },
        ]}
      />

      <main className="portal-content portal-content-narrow">

        <div className="dashboard-header">

          <h1>{doctor.full_name}</h1>

          <p>{listed}</p>

        </div>


        {/* ====================================
            TABS
        ==================================== */}


        {/* ====================================
            MY PATIENTS
        ==================================== */}

        {tab === "patients" && (

          <div className="dashboard-card">

            {patientsError && (
              <div className="error-message">{patientsError}</div>
            )}

            {loadingPatients ? (

              <div className="dashboard-loading">
                <div className="loading-spinner"></div>
                <p>Loading your patients…</p>
              </div>

            ) : myPatients.length === 0 ? (

              <div className="empty-state">
                <p>
                  No patients yet. Use Find patient to send an access
                  request by Health ID.
                </p>
              </div>

            ) : (

              <div className="entity-list">

                {myPatients.map((request) => (

                  <div
                    className="entity-card entity-card-clickable"
                    key={request.id}
                    onClick={() => openPatientRecord(request.patient.id)}
                  >

                    <div className="entity-main">

                      <div className="entity-title-row">

                        <h3>{request.patient.full_name}</h3>

                        <span className="mono" style={{ fontSize: 11.5, color: "#7d93a3" }}>
                          {request.patient.health_id}
                        </span>

                      </div>

                      <p className="entity-sub">
                        Approved access
                        {request.decided_at
                          ? ` · since ${formatDate(request.decided_at)}`
                          : ""}
                      </p>

                    </div>

                  </div>

                ))}

              </div>

            )}

          </div>

        )}


        {/* ====================================
            FIND PATIENT
        ==================================== */}

        {tab === "find" && (

          <div className="dashboard-card">

            <h3 className="form-section-title">Find a patient</h3>

            <form onSubmit={handleLookup}>

              {lookupError && (
                <div className="error-message">{lookupError}</div>
              )}

              <div className="form-row">

                <div className="form-group" style={{ flex: 1 }}>
                  <label>Patient Health ID</label>
                  <input
                    className="form-input mono"
                    value={healthIdInput}
                    onChange={(event) => setHealthIdInput(event.target.value)}
                    placeholder="e.g. 9214 7736 0025"
                  />
                  <p className="field-hint">
                    Ask the patient for the Health ID on their card,
                    dashboard, or QR code.
                  </p>
                </div>

              </div>

              <div className="form-actions">

                <button className="primary-btn" type="submit" disabled={lookingUp}>
                  {lookingUp ? "Looking up…" : "Find patient"}
                </button>

                {lookupResult && (
                  <button className="secondary-btn" type="button" onClick={resetLookup}>
                    Clear
                  </button>
                )}

              </div>

            </form>


            {lookupResult && (

              <div className="portal-note" style={{ marginTop: 20 }}>

                <div className="entity-title-row" style={{ marginBottom: 6 }}>

                  <h3 style={{ margin: 0 }}>{lookupResult.full_name}</h3>

                  {lookupResult.access_status === "approved" && (
                    <span className="pill pill-ok">You already have access</span>
                  )}

                  {lookupResult.access_status === "pending" && (
                    <span className="pill pill-warn">Request pending</span>
                  )}

                </div>

                <p className="entity-sub" style={{ marginBottom: 14 }}>
                  {[
                    lookupResult.age ? `${lookupResult.age} years` : null,
                    lookupResult.gender,
                  ]
                    .filter(Boolean)
                    .join(" · ")}{" "}
                  <span className="mono">{lookupResult.health_id}</span>
                </p>

                {requestMessage && (
                  <div className="success-message">{requestMessage}</div>
                )}

                {lookupResult.access_status === "approved" ? (

                  <button
                    className="primary-btn compact-btn"
                    onClick={() => openPatientRecord(lookupResult.id)}
                  >
                    Open record
                  </button>

                ) : lookupResult.access_status === "pending" ? (

                  <p className="field-hint">
                    Waiting on {lookupResult.full_name} to approve or
                    deny this request.
                  </p>

                ) : (

                  <form onSubmit={handleSendRequest}>

                    <div className="form-group">
                      <label>Note to the patient (optional)</label>
                      <textarea
                        className="form-input"
                        rows={3}
                        value={requestNote}
                        onChange={(event) => setRequestNote(event.target.value)}
                        placeholder="e.g. Requesting full record access for your upcoming visit"
                      />
                    </div>

                    <div className="form-actions">
                      <button
                        className="primary-btn"
                        type="submit"
                        disabled={sendingRequest}
                      >
                        {sendingRequest ? "Sending…" : "Send access request"}
                      </button>
                    </div>

                  </form>

                )}

              </div>

            )}

          </div>

        )}


        {/* ====================================
            YOUR PROFILE
        ==================================== */}

        {tab === "profile" && (

          <>

            <div className="dashboard-card info-block">

              <h3>Your details</h3>

              <p className="info-block-note">
                Held by {doctor.hospital || "your hospital"}. Anything
                wrong here is theirs to correct.
              </p>

              <div className="info-grid">

                <div className="info-item">
                  <span>Doctor ID</span>
                  <strong className="mono">{doctor.login_id || "—"}</strong>
                </div>

                <div className="info-item">
                  <span>Specialty</span>
                  <strong>{doctor.specialty}</strong>
                </div>

                <div className="info-item">
                  <span>Qualifications</span>
                  <strong>{doctor.qualification || "—"}</strong>
                </div>

                <div className="info-item">
                  <span>Experience</span>
                  <strong>
                    {doctor.experience_years
                      ? `${doctor.experience_years} years`
                      : "—"}
                  </strong>
                </div>

                <div className="info-item">
                  <span>Email</span>
                  <strong>{doctor.email || "—"}</strong>
                </div>

                <div className="info-item">
                  <span>Phone</span>
                  <strong>{doctor.phone || "—"}</strong>
                </div>

                <div className="info-item">
                  <span>Hospital</span>
                  <strong>{doctor.hospital || "—"}</strong>
                </div>

                <div className="info-item">
                  <span>Where</span>
                  <strong>
                    {[doctor.area, doctor.city].filter(Boolean).join(", ") || "—"}
                  </strong>
                </div>

              </div>

            </div>


            <div className="dashboard-card info-block">

              <h3>How patients find you</h3>

              <p className="info-block-note">
                This is what a patient sees when you come up in a
                recommendation, and what the ranking is based on.
              </p>

              <div className="info-grid">

                <div className="info-item">
                  <span>Consultation fee</span>
                  <strong>
                    {doctor.consultation_fee != null
                      ? `₹${doctor.consultation_fee}`
                      : "—"}
                  </strong>
                </div>

                <div className="info-item">
                  <span>Days</span>
                  <strong>{doctor.available_days || "—"}</strong>
                </div>

                <div className="info-item">
                  <span>Next free slot</span>
                  <strong>{doctor.next_available || "—"}</strong>
                </div>

                <div className="info-item">
                  <span>Emergencies</span>
                  <strong>
                    {doctor.handles_emergencies ? "Yes" : "No"}
                  </strong>
                </div>

                <div className="info-item">
                  <span>Rating</span>
                  <strong>
                    {doctor.reviews_count > 0
                      ? `${doctor.rating} from ${doctor.reviews_count} reviews`
                      : "No reviews yet"}
                  </strong>
                </div>

              </div>

              {doctor.focus_list?.length > 0 && (

                <div className="chip-row">

                  <span className="chip-row-label">
                    Conditions you're listed for
                  </span>

                  <div className="chip-group">
                    {doctor.focus_list.map((item) => (
                      <span className="specialty-chip" key={item}>
                        {item}
                      </span>
                    ))}
                  </div>

                </div>

              )}

              {doctor.language_list?.length > 0 && (

                <div className="chip-row">

                  <span className="chip-row-label">Languages</span>

                  <div className="chip-group">
                    {doctor.language_list.map((item) => (
                      <span className="specialty-chip" key={item}>
                        {item}
                      </span>
                    ))}
                  </div>

                </div>

              )}

            </div>


            <div className="dashboard-card info-block">

              <h3>Your account</h3>

              <p className="info-block-note">
                You sign in with your doctor ID, not your email address.
              </p>

              <button
                className="secondary-btn"
                onClick={() => navigate("/change-password")}
              >
                Change password
              </button>

            </div>

          </>

        )}

      </main>

    </div>
  );
}

export default DoctorDashboard;
