import { useEffect, useState } from "react";

import {
  uploadReport,
  getReports,
  summarizeReport,
  getReportFileUrl
} from "../services/api";

import AppNav from "../components/AppNav";

import RichText from "../components/RichText";

import Icon from "../components/Icon";


function MedicalReports() {

  // ============================================================
  // STATE
  // ============================================================

  const [reports, setReports] = useState([]);

  const [error, setError] = useState("");

  const [message, setMessage] = useState("");

  const [loadingReports, setLoadingReports] = useState(true);

  const [uploading, setUploading] = useState(false);

  const [summarizingId, setSummarizingId] = useState(null);

  const [typeFilter, setTypeFilter] = useState("all");

  const [statusFilter, setStatusFilter] = useState("all");

  const [showUpload, setShowUpload] = useState(false);

  // Report ids whose summary panel is open. Every summary starts
  // closed - it opens when the person asks for it and closes on the
  // next click. Nothing is persisted, so a page reload starts closed.
  const [openIds, setOpenIds] = useState([]);


  const [form, setForm] = useState({
    report_name: "",
    report_type: "",
    file: null
  });


  // ============================================================
  // REPORT TYPES
  // ============================================================

  const reportTypes = [
    { value: "cbc", label: "CBC", icon: "🩸" },
    { value: "blood", label: "Blood Test", icon: "🧪" },
    { value: "lipid", label: "Lipid Profile", icon: "❤️" },
    { value: "diabetes", label: "Diabetes", icon: "🩺" },
    { value: "liver", label: "Liver Function", icon: "🫀" },
    { value: "kidney", label: "Kidney Function", icon: "🫘" },
    { value: "thyroid", label: "Thyroid", icon: "🦋" },
    { value: "urine", label: "Urine Test", icon: "🧪" },
    { value: "vitamin", label: "Vitamin Test", icon: "💊" },
    { value: "hormone", label: "Hormone Test", icon: "🔬" },
    { value: "imaging", label: "Imaging", icon: "🩻" },
    { value: "pathology", label: "Pathology", icon: "🔬" },
    { value: "cardiac", label: "Cardiac", icon: "❤️" },
    { value: "other", label: "Other", icon: "📋" }
  ];


  // ============================================================
  // INITIAL LOAD
  // ============================================================

  useEffect(() => {
    loadReports();
  }, []);


  // ============================================================
  // LOAD REPORTS
  // ============================================================

  async function loadReports() {

    try {

      setError("");

      setLoadingReports(true);

      const data = await getReports();

      setReports(Array.isArray(data) ? data : []);

    } catch (loadError) {

      setError(
        loadError.message ||
        "Could not load your reports. Refresh to try again."
      );

    } finally {

      setLoadingReports(false);

    }
  }


  // ============================================================
  // FORM CHANGE
  // ============================================================

  function handleChange(event) {

    const { name, value, files } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: files ? files[0] : value
    }));
  }


  // ============================================================
  // UPLOAD REPORT
  // ============================================================
  //
  // The backend now indexes the report, writes its own summary, and
  // refreshes the combined health summary before this call returns -
  // so once it resolves, reloading the list is enough to show the
  // explanation. Nothing else has to be triggered.

  async function handleUpload(event) {

    event.preventDefault();

    setError("");

    setMessage("");


    if (!form.report_name.trim()) {
      setError("Enter a name for this report.");
      return;
    }

    if (!form.report_type) {
      setError("Choose a report type.");
      return;
    }

    if (!form.file) {
      setError("Choose a report file to upload.");
      return;
    }


    setUploading(true);


    try {

      const formData = new FormData();

      formData.append("report_name", form.report_name.trim());

      formData.append("report_type", form.report_type);

      formData.append("file", form.file);


      const result = await uploadReport(formData);


      if (result.status === "summarized") {

        setMessage(
          "Report uploaded. Open its summary from the list below."
        );

      } else if (result.status === "failed") {

        setError(
          result.error_message ||
          "The report was saved, but its summary could not be generated. Use Summarize to try again."
        );

      } else {

        setMessage(
          "Report uploaded. No readable results were found in it yet."
        );

      }


      setForm({
        report_name: "",
        report_type: "",
        file: null
      });

      setShowUpload(false);


      // The list reflects work the upload request already finished.
      await loadReports();


    } catch (uploadError) {

      setError(
        uploadError.message ||
        "The upload did not go through. Check the file and try again."
      );

    } finally {

      setUploading(false);

    }
  }


  // ============================================================
  // SUMMARIZE (REGENERATE ONE REPORT'S EXPLANATION)
  // ============================================================

  async function handleSummarize(reportId) {

    setError("");

    setMessage("");

    setSummarizingId(reportId);


    try {

      const result = await summarizeReport(reportId);


      if (result.status === "summarized") {

        setMessage("Summary updated.");

        // Open the panel so the person sees what they just asked for.
        setOpenIds((previous) =>
          previous.includes(reportId) ? previous : [...previous, reportId]
        );

      } else {

        setError(
          result.error_message ||
          "The summary could not be generated for this report."
        );

      }


      await loadReports();


    } catch (summarizeError) {

      setError(
        summarizeError.message ||
        "The summary could not be generated for this report."
      );

    } finally {

      setSummarizingId(null);

    }
  }


  // ============================================================
  // OPEN / CLOSE A SUMMARY
  // ============================================================

  function toggleSummary(reportId) {

    setOpenIds((previous) =>

      previous.includes(reportId)

        ? previous.filter((id) => id !== reportId)

        : [...previous, reportId]
    );
  }

  // ============================================================
  // HELPERS
  // ============================================================

  function getReportType(reportType) {

    return (
      reportTypes.find((type) => type.value === reportType) || {
        label: reportType || "Other",
        icon: "📋"
      }
    );
  }


  function formatDate(value) {

    if (!value) {
      return null;
    }

    return new Date(value).toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric"
    });
  }


  // ============================================================
  // FILTER REPORTS
  // ============================================================

  const filteredReports = reports.filter((report) => {

    const typeMatch =
      typeFilter === "all" ||
      report.report_type?.toLowerCase() === typeFilter;

    const statusMatch =
      statusFilter === "all" ||
      report.status === statusFilter;

    return typeMatch && statusMatch;
  });


  // ============================================================
  // COUNTS
  // ============================================================

  const summarizedCount = reports.filter(
    (report) => report.status === "summarized"
  ).length;

  const needsAttentionCount = reports.filter(
    (report) => report.status !== "summarized"
  ).length;


  // ============================================================
  // PAGE
  // ============================================================

  return (

    <div className="reports-page">


      {/* ======================================================
          NAVBAR
      ====================================================== */}

      <AppNav active="reports" />


      {/* ======================================================
          MAIN CONTENT
      ====================================================== */}

      <main className="reports-content">


        {/* ====================================================
            HEADER
        ==================================================== */}

        <div className="reports-header">

          <div>

            <h1>Medical Reports</h1>

            <p>
              Every report is read and explained as soon as you upload it.
            </p>

          </div>

          <button
            className="primary-btn"
            onClick={() => {
              setShowUpload(!showUpload);
              setError("");
              setMessage("");
            }}
          >
            <Icon name={showUpload ? "close" : "upload"} size={18} />
            {showUpload ? "Close" : "Upload report"}
          </button>

        </div>


        {/* ====================================================
            STATS
        ==================================================== */}

        <div className="report-stats">

          <div className="report-stat-card">

            <div className="report-stat-icon"><Icon name="reports" size={20} /></div>

            <div>
              <span>Total reports</span>
              <strong>{reports.length}</strong>
            </div>

          </div>

          <div className="report-stat-card">

            <div className="report-stat-icon"><Icon name="spark" size={20} /></div>

            <div>
              <span>Summarized</span>
              <strong>{summarizedCount}</strong>
            </div>

          </div>

          <div className="report-stat-card">

            <div className="report-stat-icon"><Icon name="pulse" size={20} /></div>

            <div>
              <span>Needs a retry</span>
              <strong>{needsAttentionCount}</strong>
            </div>

          </div>

        </div>


        {/* ====================================================
            MESSAGES
        ==================================================== */}

        {message && (

          <div className="success-message">
            <span className="message-icon">✓</span>
            <span>{message}</span>
          </div>

        )}

        {error && (

          <div className="error-message">
            <span className="message-icon">⚠</span>
            <span>{error}</span>
          </div>

        )}


        {/* ====================================================
            UPLOAD FORM
        ==================================================== */}

        {showUpload && (

          <div className="reports-card upload-card">

            <div className="upload-card-header">

              <div>

                <h2>Upload a medical report</h2>

                <p className="upload-description">
                  Reading the report takes a few moments. Its summary is
                  ready as soon as the upload finishes.
                </p>

              </div>

              <div className="upload-icon"><Icon name="upload" size={22} /></div>

            </div>

            <form onSubmit={handleUpload}>

              <div className="form-row">

                <div className="form-group">

                  <label>Report name</label>

                  <input
                    type="text"
                    name="report_name"
                    placeholder="e.g. CBC, March 2026"
                    value={form.report_name}
                    onChange={handleChange}
                    required
                    disabled={uploading}
                  />

                </div>

                <div className="form-group">

                  <label>Report type</label>

                  <select
                    name="report_type"
                    value={form.report_type}
                    onChange={handleChange}
                    required
                    disabled={uploading}
                  >

                    <option value="">Choose a type</option>

                    {reportTypes.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}

                  </select>

                </div>

              </div>


              <div className="form-group">

                <label>Report file</label>

                <div className="file-input-wrapper">

                  <input
                    type="file"
                    name="file"
                    accept="application/pdf,.pdf"
                    onChange={handleChange}
                    required
                    disabled={uploading}
                  />

                </div>

                <small className="file-help">
                  PDF files only.
                </small>

              </div>


              {form.file && (

                <div className="selected-file">

                  <div className="selected-file-icon"><Icon name="file" size={20} /></div>

                  <div className="selected-file-info">

                    <strong>{form.file.name}</strong>

                    <small>
                      {(form.file.size / 1024 / 1024).toFixed(2)} MB
                    </small>

                  </div>

                  <div className="file-ready">Ready</div>

                </div>

              )}


              <div className="upload-actions">

                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => {
                    setShowUpload(false);
                    setForm({
                      report_name: "",
                      report_type: "",
                      file: null
                    });
                    setError("");
                  }}
                  disabled={uploading}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="primary-btn upload-submit-btn"
                  disabled={uploading}
                >

                  {uploading ? (
                    <>
                      <span className="spinner"></span>
                      Reading your report…
                    </>
                  ) : (
                    <>Upload report</>
                  )}

                </button>

              </div>

            </form>

          </div>

        )}


        {/* ====================================================
            FILTERS
        ==================================================== */}

        <div className="reports-card filters-card">

          <div className="filter-section">

            <label>Report type</label>

            <div className="filter-buttons">

              <button
                className={
                  typeFilter === "all"
                    ? "filter-btn active"
                    : "filter-btn"
                }
                onClick={() => setTypeFilter("all")}
              >
                All
              </button>

              {reportTypes.map((type) => (

                <button
                  key={type.value}
                  className={
                    typeFilter === type.value
                      ? "filter-btn active"
                      : "filter-btn"
                  }
                  onClick={() => setTypeFilter(type.value)}
                >
                  {type.label}
                </button>

              ))}

            </div>

          </div>


          <div className="filter-section">

            <label>Status</label>

            <div className="filter-buttons">

              <button
                className={
                  statusFilter === "all"
                    ? "filter-btn active"
                    : "filter-btn"
                }
                onClick={() => setStatusFilter("all")}
              >
                All
              </button>

              <button
                className={
                  statusFilter === "summarized"
                    ? "filter-btn active"
                    : "filter-btn"
                }
                onClick={() => setStatusFilter("summarized")}
              >
                Summarized
              </button>

              <button
                className={
                  statusFilter === "failed"
                    ? "filter-btn active"
                    : "filter-btn"
                }
                onClick={() => setStatusFilter("failed")}
              >
                Needs a retry
              </button>

            </div>

          </div>

        </div>


        {/* ====================================================
            REPORT LIST
        ==================================================== */}

        <div className="reports-card">

          <div className="reports-card-header">

            <div>

              <h2>My reports</h2>

              <p className="reports-count-text">
                Each report is followed by its own explanation.
              </p>

            </div>

            <span className="reports-count">
              {filteredReports.length}{" "}
              {filteredReports.length === 1 ? "report" : "reports"}
            </span>

          </div>


          {loadingReports ? (

            <div className="reports-loading">
              <span className="large-spinner"></span>
              <p>Loading your reports…</p>
            </div>

          ) : filteredReports.length === 0 ? (

            <div className="empty-reports">

              <div className="empty-icon"><Icon name="reports" size={34} /></div>

              <h3>Nothing here yet</h3>

              <p>Upload a medical report to see it and its summary here.</p>

              <button
                className="primary-btn"
                onClick={() => {
                  setShowUpload(true);
                  setTypeFilter("all");
                  setStatusFilter("all");
                }}
              >
                + Upload report
              </button>

            </div>

          ) : (

            <div className="report-list">

              {filteredReports.map((report) => {

                const type = getReportType(report.report_type);

                const isSummarizing = summarizingId === report.id;

                const isOpen = openIds.includes(report.id);

                return (

                  <article className="report-entry" key={report.id}>


                    {/* ------------------------------------------
                        ROW
                    ------------------------------------------ */}

                    <div className="report-item">

                      <div className="report-icon"><Icon name="file" size={22} /></div>


                      <div className="report-info">

                        <div className="report-title-row">

                          <h3>{report.report_name}</h3>

                          <span className="report-type-badge">
                            {type.label}
                          </span>

                          {report.status === "summarized" ? (
                            <span className="status-pill status-summarized">
                              Summarized
                            </span>
                          ) : report.status === "failed" ? (
                            <span className="status-pill status-failed">
                              Needs a retry
                            </span>
                          ) : (
                            <span className="status-pill status-processing">
                              No results read
                            </span>
                          )}

                          {report.uploaded_by === "hospital" && (
                            <span className="status-pill status-summarized">
                              Uploaded by {report.uploaded_by_hospital}
                            </span>
                          )}

                        </div>

                        <p className="report-meta">
                          Uploaded {formatDate(report.uploaded_at) || "recently"}
                          {report.observation_count
                            ? ` · ${report.observation_count} results read`
                            : ""}
                          {report.uploaded_by === "hospital" &&
                          report.uploaded_by_staff
                            ? ` · Recorded by ${report.uploaded_by_staff}`
                            : ""}
                        </p>

                      </div>


                      <div className="report-actions">

                        {report.ai_summary ? (

                          <button
                            className={
                              isOpen
                                ? "summarize-btn is-open"
                                : "summarize-btn"
                            }
                            onClick={() => toggleSummary(report.id)}
                            aria-expanded={isOpen}
                            aria-controls={`summary-${report.id}`}
                            disabled={isSummarizing}
                          >
                            {isOpen ? "Hide summary" : "View summary"}
                            <span className="chevron" aria-hidden="true">
                              ▾
                            </span>
                          </button>

                        ) : (

                          <button
                            className="summarize-btn"
                            onClick={() => handleSummarize(report.id)}
                            disabled={isSummarizing}
                          >
                            {isSummarizing ? (
                              <>
                                <span className="spinner"></span>
                                Summarizing…
                              </>
                            ) : (
                              <>Summarize</>
                            )}
                          </button>

                        )}

                        <a
                          href={getReportFileUrl(report)}
                          target="_blank"
                          rel="noreferrer"
                          className="view-btn"
                        >
                          View PDF
                        </a>

                      </div>

                    </div>


                    {/* ------------------------------------------
                        THIS REPORT'S SUMMARY - directly beneath
                        the report it belongs to.
                    ------------------------------------------ */}

                    {isSummarizing ? (

                      <div className="report-summary report-summary-busy">
                        <span className="spinner"></span>
                        <span>Reading this report…</span>
                      </div>

                    ) : report.ai_summary ? (

                      isOpen && (

                        <div
                          className="report-summary"
                          id={`summary-${report.id}`}
                        >

                          <div className="report-summary-bar">

                            <span className="report-summary-title">
                              Summary of this report
                            </span>

                            <button
                              className="link-btn"
                              onClick={() => handleSummarize(report.id)}
                            >
                              Regenerate
                            </button>

                          </div>

                          <RichText className="report-summary-body">
                            {report.ai_summary}
                          </RichText>

                          <p className="report-summary-note">
                            This explains your results in plain language.
                            It is not a diagnosis — go through it with
                            your doctor.
                          </p>

                        </div>

                      )

                    ) : report.error_message ? (

                      <div className="report-summary report-summary-empty">
                        <p>
                          This report could not be read:{" "}
                          {report.error_message}
                        </p>
                      </div>

                    ) : null}

                  </article>
                );
              })}

            </div>

          )}

        </div>

      </main>

    </div>
  );
}


export default MedicalReports;
