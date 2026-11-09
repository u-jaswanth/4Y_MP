import { useEffect, useState } from "react";

import {
  getDoctorOptions,
  recommendDoctors
} from "../services/api";

import AppNav from "../components/AppNav";


const SEVERITY_ORDER = ["mild", "moderate", "severe"];

const URGENCY_COPY = {
  emergency: {
    label: "Go to an emergency room now",
    tone: "urgency-emergency"
  },
  urgent: {
    label: "See someone today or tomorrow",
    tone: "urgency-urgent"
  },
  routine: {
    label: "A regular appointment is fine",
    tone: "urgency-routine"
  }
};


function DoctorRecommendation() {

  // ============================================================
  // STATE
  // ============================================================

  const [options, setOptions] = useState(null);

  const [form, setForm] = useState({
    concern: "",
    symptoms: "",
    duration: "",
    severity: "",
    area: "",
    city: "Hyderabad"
  });

  const [result, setResult] = useState(null);

  const [searching, setSearching] = useState(false);

  const [error, setError] = useState("");


  // ============================================================
  // LOAD DROPDOWN OPTIONS
  // ============================================================

  useEffect(() => {

    async function loadOptions() {

      try {

        const data = await getDoctorOptions();

        setOptions(data);

        setForm((previous) => ({
          ...previous,
          city: data.cities?.[0] || "Hyderabad"
        }));

      } catch (optionsError) {

        setError(
          optionsError.message ||
          "Could not load the form. Refresh to try again."
        );

      }
    }

    loadOptions();

  }, []);


  // ============================================================
  // FORM
  // ============================================================

  function handleChange(event) {

    const { name, value } = event.target;

    setForm((previous) => ({ ...previous, [name]: value }));
  }


  function isComplete() {
    return (
      form.concern &&
      form.symptoms.trim().length >= 5 &&
      form.duration &&
      form.severity &&
      form.area
    );
  }


  async function handleSubmit(event) {

    event.preventDefault();

    setError("");

    if (!isComplete()) {
      setError(
        "Fill in every field, and describe the symptoms in a sentence or two."
      );
      return;
    }

    setSearching(true);

    try {

      const data = await recommendDoctors({
        ...form,
        symptoms: form.symptoms.trim()
      });

      setResult(data);

      // Drop the reader at the results rather than leaving them
      // looking at the form they just submitted.
      window.scrollTo({ top: 0, behavior: "smooth" });

    } catch (searchError) {

      setError(
        searchError.message ||
        "Could not find doctors for this case. Try again in a moment."
      );

    } finally {

      setSearching(false);

    }
  }


  function startOver() {
    setResult(null);
    setError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }


  // ============================================================
  // PAGE
  // ============================================================

  const urgency = result
    ? URGENCY_COPY[result.urgency] || URGENCY_COPY.routine
    : null;


  return (

    <div className="dashboard-page">

      <AppNav active="doctors" />

      <main className="dashboard-content">


        <div className="dashboard-header">

          <h1>Find a doctor</h1>

          <p>
            Describe what's going on and we'll work out which specialist
            fits, then rank the ones near you.
          </p>

        </div>


        {error && (

          <div className="error-message">
            <span className="message-icon">⚠</span>
            <span>{error}</span>
          </div>

        )}


        {/* ====================================================
            RESULTS
        ==================================================== */}

        {result && (

          <>

            {/* ------------- urgent banner ------------- */}

            {result.red_flags.length > 0 && (

              <div
                className={`urgency-banner ${
                  result.urgency === "emergency"
                    ? "urgency-banner-emergency"
                    : "urgency-banner-urgent"
                }`}
              >

                <div className="urgency-banner-title">
                  {result.urgency === "emergency"
                    ? "This needs emergency care"
                    : "Don't wait on this"}
                </div>

                {result.red_flags.map((flag, index) => (
                  <p key={index}>{flag}</p>
                ))}

                {result.urgency === "emergency" && (
                  <p className="urgency-banner-action">
                    Call 108 for an ambulance, or go to the nearest
                    hospital emergency department. The list below is for
                    follow-up care, not for right now.
                  </p>
                )}

              </div>

            )}


            {/* ------------- what we understood ------------- */}

            <div className="dashboard-card case-card">

              <div className="case-card-header">

                <div>

                  <h3>What we understood</h3>

                  <p className="case-card-sub">
                    {result.ai_reading_used
                      ? "Read from your description and your saved reports"
                      : "Matched from your description"}
                  </p>

                </div>

                <span className={`urgency-chip ${urgency.tone}`}>
                  {urgency.label}
                </span>

              </div>

              <p className="case-summary">{result.case_summary}</p>

              <div className="specialty-row">

                <span className="specialty-row-label">
                  Best suited to
                </span>

                {result.specialties.map((specialty, index) => (
                  <span
                    key={specialty}
                    className={
                      index === 0
                        ? "specialty-chip specialty-chip-primary"
                        : "specialty-chip"
                    }
                  >
                    {specialty}
                  </span>
                ))}

              </div>

            </div>


            {/* ------------- ranked doctors ------------- */}

            <div className="dashboard-card">

              <div className="reports-card-header">

                <div>
                  <h3>Doctors near {form.area}</h3>
                  <p className="reports-count-text">
                    Ranked on specialty, distance, rating, experience
                    and who can see you soonest.
                  </p>
                </div>

                <span className="reports-count">
                  {result.matches.length} matches
                </span>

              </div>


              <div className="doctor-list">

                {result.matches.map((match, index) => (

                  <article className="doctor-card" key={match.doctor.id}>

                    <div className="doctor-card-main">

                      <div className="doctor-avatar">
                        {match.doctor.full_name
                          .replace("Dr. ", "")
                          .charAt(0)}
                      </div>

                      <div className="doctor-identity">

                        <div className="doctor-name-row">

                          <h4>{match.doctor.full_name}</h4>

                          {index === 0 && (
                            <span className="best-match-tag">
                              Best match
                            </span>
                          )}

                        </div>

                        <p className="doctor-credentials">
                          {match.doctor.specialty}
                          {match.doctor.qualification
                            ? ` · ${match.doctor.qualification}`
                            : ""}
                        </p>

                        <p className="doctor-credentials">
                          {match.doctor.experience_years} years experience
                          {match.doctor.language_list.length > 0
                            ? ` · speaks ${match.doctor.language_list.join(", ")}`
                            : ""}
                        </p>

                      </div>

                      <div className="doctor-score">

                        <div
                          className="score-dial"
                          style={{
                            background: `conic-gradient(#0e6e5d ${
                              match.match_score * 3.6
                            }deg, #e7ebe8 0deg)`
                          }}
                        >
                          <span>{match.match_score}</span>
                        </div>

                        <small>match</small>

                      </div>

                    </div>


                    <div className="doctor-facts">

                      <div className="doctor-fact">
                        <span>Where</span>
                        <strong>
                          {match.doctor.hospital}, {match.doctor.area}
                        </strong>
                      </div>

                      <div className="doctor-fact">
                        <span>Distance</span>
                        <strong>{match.distance_label}</strong>
                      </div>

                      <div className="doctor-fact">
                        <span>Next slot</span>
                        <strong>{match.doctor.next_available}</strong>
                      </div>

                      <div className="doctor-fact">
                        <span>Consultation</span>
                        <strong>₹{match.doctor.consultation_fee}</strong>
                      </div>

                      <div className="doctor-fact">
                        <span>Rating</span>
                        <strong>
                          {match.doctor.rating} ({match.doctor.reviews_count})
                        </strong>
                      </div>

                      <div className="doctor-fact">
                        <span>Days</span>
                        <strong>{match.doctor.available_days}</strong>
                      </div>

                    </div>


                    {match.reasons.length > 0 && (

                      <div className="doctor-reasons">

                        <span className="doctor-reasons-label">
                          Why this one
                        </span>

                        <ul>
                          {match.reasons.map((reason, reasonIndex) => (
                            <li key={reasonIndex}>{reason}</li>
                          ))}
                        </ul>

                      </div>

                    )}


                    {match.doctor.focus_list.length > 0 && (

                      <div className="doctor-tags">
                        {match.doctor.focus_list.slice(0, 5).map((tag) => (
                          <span key={tag} className="doctor-tag">
                            {tag}
                          </span>
                        ))}
                      </div>

                    )}

                  </article>

                ))}

              </div>

            </div>


            {/* ------------- prep ------------- */}

            <div className="dashboard-grid">

              <div className="dashboard-card">

                <h3>Ask at the appointment</h3>

                <ul className="plain-list">
                  {result.questions_for_doctor.map((question, index) => (
                    <li key={index}>{question}</li>
                  ))}
                </ul>

              </div>

              <div className="dashboard-card">

                <h3>Before you go</h3>

                <ul className="plain-list">
                  {result.before_the_visit.map((item, index) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>

              </div>

            </div>


            <div className="results-footer">

              <p className="disclaimer">
                These suggestions are generated from what you typed and
                are not a diagnosis. The directory is sample data for
                development. If anything gets worse, see a doctor in
                person.
              </p>

              <button className="secondary-btn" onClick={startOver}>
                Describe something else
              </button>

            </div>

          </>

        )}


        {/* ====================================================
            FORM
        ==================================================== */}

        {!result && (

          <div className="dashboard-card intake-card">

            {!options ? (

              <div className="summary-loading">
                <div className="loading-spinner"></div>
                <p>Loading the form…</p>
              </div>

            ) : (

              <form onSubmit={handleSubmit}>

                {/* 1 ------------------------------------------- */}

                <div className="intake-field">

                  <label htmlFor="concern">
                    What kind of problem is it?
                  </label>

                  <select
                    id="concern"
                    name="concern"
                    value={form.concern}
                    onChange={handleChange}
                    disabled={searching}
                  >

                    <option value="">Choose one</option>

                    {options.concerns.map((concern) => (
                      <option key={concern.value} value={concern.value}>
                        {concern.label}
                      </option>
                    ))}

                  </select>

                  <small>
                    Pick "Not sure" and we'll work it out from your
                    description.
                  </small>

                </div>


                {/* 2 ------------------------------------------- */}

                <div className="intake-field">

                  <label htmlFor="symptoms">
                    Describe what you're feeling
                  </label>

                  <textarea
                    id="symptoms"
                    name="symptoms"
                    rows={5}
                    value={form.symptoms}
                    onChange={handleChange}
                    disabled={searching}
                    placeholder={
                      "In your own words. For example: sharp pain in my " +
                      "lower back since Monday, worse when I sit for long, " +
                      "and it spreads down my right leg."
                    }
                  />

                  <small>
                    The more specific you are, the better the match.
                    Mention where it hurts, when it started and what
                    makes it worse.
                  </small>

                </div>


                {/* 3 + 4 --------------------------------------- */}

                <div className="intake-row">

                  <div className="intake-field">

                    <label htmlFor="duration">
                      How long has it been going on?
                    </label>

                    <select
                      id="duration"
                      name="duration"
                      value={form.duration}
                      onChange={handleChange}
                      disabled={searching}
                    >

                      <option value="">Choose one</option>

                      {options.durations.map((duration) => (
                        <option key={duration.value} value={duration.value}>
                          {duration.label}
                        </option>
                      ))}

                    </select>

                  </div>

                  <div className="intake-field">

                    <label>How bad is it?</label>

                    <div className="severity-group">

                      {SEVERITY_ORDER.map((value) => {

                        const option = options.severities.find(
                          (item) => item.value === value
                        );

                        if (!option) {
                          return null;
                        }

                        return (

                          <button
                            type="button"
                            key={value}
                            className={
                              form.severity === value
                                ? `severity-btn severity-${value} active`
                                : `severity-btn severity-${value}`
                            }
                            onClick={() =>
                              setForm((previous) => ({
                                ...previous,
                                severity: value
                              }))
                            }
                            disabled={searching}
                            title={option.label}
                          >
                            {option.label.split(" - ")[0]}
                          </button>
                        );
                      })}

                    </div>

                    <small>
                      {options.severities.find(
                        (item) => item.value === form.severity
                      )?.label || "Mild, moderate or severe."}
                    </small>

                  </div>

                </div>


                {/* 5 ------------------------------------------- */}

                <div className="intake-row">

                  <div className="intake-field">

                    <label htmlFor="city">City</label>

                    <select
                      id="city"
                      name="city"
                      value={form.city}
                      onChange={handleChange}
                      disabled={searching}
                    >
                      {options.cities.map((city) => (
                        <option key={city} value={city}>
                          {city}
                        </option>
                      ))}
                    </select>

                    <small>
                      Only Hyderabad is in the directory right now.
                    </small>

                  </div>

                  <div className="intake-field">

                    <label htmlFor="area">Your area</label>

                    <select
                      id="area"
                      name="area"
                      value={form.area}
                      onChange={handleChange}
                      disabled={searching}
                    >

                      <option value="">Choose your area</option>

                      {options.areas.map((area) => (
                        <option key={area} value={area}>
                          {area}
                        </option>
                      ))}

                    </select>

                    <small>
                      Used to measure how far each clinic is from you.
                    </small>

                  </div>

                </div>


                <div className="intake-actions">

                  <button
                    type="submit"
                    className="primary-btn"
                    disabled={searching || !isComplete()}
                  >

                    {searching ? (
                      <>
                        <span className="spinner"></span>
                        Reading your case…
                      </>
                    ) : (
                      <>Find doctors</>
                    )}

                  </button>

                  <p className="disclaimer">
                    Not a diagnosis, and not a substitute for seeing a
                    doctor. In an emergency, call 108.
                  </p>

                </div>

              </form>

            )}

          </div>

        )}

      </main>

    </div>
  );
}


export default DoctorRecommendation;
