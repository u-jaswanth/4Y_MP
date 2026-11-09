import { useEffect, useState } from "react";
import { QRCodeCanvas } from "qrcode.react";
import { useNavigate } from "react-router-dom";

import {
  getPatientProfile,
  getHealthSummary
} from "../services/api";

import AppNav from "../components/AppNav";

import BrandMark from "../components/BrandMark";

import Icon from "../components/Icon";

import { setDisplayName } from "../services/session";

import RichText from "../components/RichText";

import TrendsCard from "../components/TrendsCard";


// "Good morning" / "Good afternoon" / "Good evening", from the
// person's own clock rather than the server's.
function greetingFor(date = new Date()) {

  const hour = date.getHours();

  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";

  return "Good evening";
}


function Dashboard() {

  const navigate = useNavigate();

  const [patient, setPatient] = useState(null);

  const [healthSummary, setHealthSummary] = useState(null);

  const [patientLoading, setPatientLoading] = useState(true);

  const [summaryLoading, setSummaryLoading] = useState(true);

  const [error, setError] = useState("");

  // The summary is clamped to a short preview; this opens it fully.
  const [summaryExpanded, setSummaryExpanded] = useState(false);


  // ==========================================
  // LOAD PATIENT
  // ==========================================

  useEffect(() => {

    async function loadPatient() {

      try {

        setPatientLoading(true);

        const data = await getPatientProfile();

        setPatient(data);

        // The sidebar shows who is signed in; it reads this on every tab.
        setDisplayName(data.full_name);

      } catch (error) {

        setError(error.message);

      } finally {

        setPatientLoading(false);

      }

    }

    loadPatient();

  }, []);


  // ==========================================
  // LOAD AI SUMMARY
  // ==========================================

  useEffect(() => {

    async function loadSummary() {

      try {

        setSummaryLoading(true);

        const data = await getHealthSummary();

        setHealthSummary(data);

      } catch (error) {

        console.error(
          "Failed to load health summary:",
          error
        );

      } finally {

        setSummaryLoading(false);

      }

    }

    loadSummary();

  }, []);

  // ==========================================
  // PATIENT LOADING
  // ==========================================

  if (patientLoading) {

    return (

      <div className="dashboard-loading">

        <div className="loading-spinner"></div>

        <p>
          Loading your health profile...
        </p>

      </div>

    );

  }


  // ==========================================
  // ERROR
  // ==========================================

  if (error) {

    return (

      <div className="auth-container">

        <div className="auth-card">

          <div className="error-message">

            {error}

          </div>

          <button
            className="primary-btn"
            onClick={() => navigate("/login")}
          >
            Back to Login
          </button>

        </div>

      </div>

    );

  }


  // ==========================================
  // DASHBOARD
  // ==========================================

  return (

    <div className="dashboard-page">


      {/* ======================================
          NAVBAR
      ====================================== */}

      <AppNav active="dashboard" />



      {/* ======================================
          MAIN CONTENT
      ====================================== */}

      <main className="dashboard-content">


        {/* ====================================
            HEADER
        ==================================== */}

        <header className="dashboard-header page-head">

          <div>

            <h1>
              {greetingFor()}, {patient.full_name.split(" ")[0]}
            </h1>

            <p>
              Here is where your health stands today.
            </p>

          </div>

          <div className="page-actions">

            <button
              className="secondary-btn"
              onClick={() => navigate("/chat")}
            >
              <Icon name="chat" size={18} />
              Ask AI
            </button>

            <button
              className="primary-btn"
              onClick={() => navigate("/reports")}
            >
              <Icon name="upload" size={18} />
              Upload report
            </button>

          </div>

        </header>


        <div className="dash-layout">

          <div className="dash-main">


        {/* ====================================
            AI HEALTH SUMMARY
        ==================================== */}

        <div className="dashboard-card ai-summary-card">

          <div className="ai-summary-header">

            <div>

              <h3>
                Your health summary
              </h3>

              <p>

                {summaryLoading

                  ? "Loading your health summary…"

                  : healthSummary &&
                    healthSummary.reports_analyzed > 0

                    ? `Across ${healthSummary.reports_analyzed} of your reports`

                    : "Upload a report and your summary appears here"

                }

              </p>

            </div>

          </div>



          {/* ==================================
              SUMMARY LOADING
          ================================== */}

          {summaryLoading ? (

            <div className="summary-loading">

              <div className="loading-spinner"></div>

              <p>
                Preparing your health summary...
              </p>

            </div>

          ) : healthSummary &&
            healthSummary.summary ? (

            <>

              {/* SUMMARY */}

              {/* The summary arrives as Markdown - RichText turns the
                  headings and bullets into real elements instead of
                  printing ## and ** into the page. */}

              <div
                className={
                  summaryExpanded || healthSummary.summary.length < 420
                    ? "ai-summary-content is-expanded"
                    : "ai-summary-content is-clamped"
                }
                id="dashboard-summary-body"
              >

                <RichText>
                  {healthSummary.summary}
                </RichText>

              </div>

              {healthSummary.summary.length >= 420 && (
              <button
                type="button"
                className="show-more-btn"
                onClick={() => setSummaryExpanded(!summaryExpanded)}
                aria-expanded={summaryExpanded}
                aria-controls="dashboard-summary-body"
              >
                {summaryExpanded ? "Show less" : "Show more"}
                <span className="chevron" aria-hidden="true">▾</span>
              </button>
              )}



              {/* STATS */}

              <div className="ai-health-stats">


                <div className="ai-stat">

                  <span>
                    Reports Analyzed
                  </span>

                  <strong>
                    {healthSummary.reports_analyzed}
                  </strong>

                </div>



                <div className="ai-stat">

                  <span>
                    Data Points Reviewed
                  </span>

                  <strong>
                    {healthSummary.observation_count}
                  </strong>

                </div>


              </div>

            </>

          ) : (

            <div className="empty-ai-summary">

              <p>
                No analyzed reports available yet.
              </p>

              <button
                className="primary-btn"
                onClick={() => navigate("/reports")}
              >
                Upload Medical Report
              </button>

            </div>

          )}

        </div>



        {/* ====================================
            HEALTH TRENDS
        ==================================== */}

        <TrendsCard />



          </div>


          <aside className="dash-rail">

        {/* ====================================
            HEALTH ID + PATIENT DETAILS
        ==================================== */}

        <div className="dashboard-grid">


          {/* ==================================
              HEALTH ID
          ================================== */}

          <div className="dashboard-card health-card">

            <div className="health-card-top">

              <BrandMark onDark size={26} />

              <span className="health-card-tag">Health ID</span>

            </div>


            <div className="qr-container">

              <QRCodeCanvas
                value={patient.health_id}
                size={168}
              />

            </div>


            <div className="health-card-id">

              <span>ID number</span>

              <div className="health-id-large">

                {patient.health_id}

              </div>

            </div>


            <p>
              Give this ID to your hospital so they
              can add reports straight to your record.
            </p>

          </div>


          {/* ==================================
              PATIENT INFORMATION
          ================================== */}

          <div className="dashboard-card">

            <h3>
              Your details
            </h3>


            <div className="profile-grid">


              <div className="profile-item">

                <label>
                  Full Name
                </label>

                <strong>
                  {patient.full_name}
                </strong>

              </div>



              <div className="profile-item">

                <label>
                  Email
                </label>

                <strong>
                  {patient.email}
                </strong>

              </div>



              <div className="profile-item">

                <label>
                  Age
                </label>

                <strong>
                  {patient.age}
                </strong>

              </div>



              <div className="profile-item">

                <label>
                  Gender
                </label>

                <strong>
                  {patient.gender}
                </strong>

              </div>



              <div className="profile-item">

                <label>
                  Mobile
                </label>

                <strong>
                  {patient.mobile}
                </strong>

              </div>



              <div className="profile-item">

                <label>
                  Account Type
                </label>

                <strong>
                  Patient
                </strong>

              </div>


            </div>

          </div>



        </div>

          </aside>

        </div>


      </main>

    </div>

  );

}


export default Dashboard;