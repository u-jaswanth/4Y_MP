import { useEffect, useState } from "react";

import PortalNav from "../components/PortalNav";
import CredentialsCard from "../components/CredentialsCard";

import {
  getHospitalProfile,
  getDoctorFormOptions,
  getHospitalDoctors,
  addDoctor,
  resetDoctorPassword,
  deleteDoctor,
  lookupPatientByHealthId,
  uploadReportForPatient,
} from "../services/portalApi";

/**
 * HospitalDashboard
 * ------------------------------------------------------------
 * Three tabs: the hospital's own details, its doctors, and uploading
 * a report straight to a patient's account by their Health ID.
 *
 * The add-doctor form is longer than it looks like it needs to be, and
 * that is on purpose. Every field on it is one the recommendation
 * engine reads when it ranks doctors for a patient's symptoms (see
 * app/doctors/recommender.py). A doctor added with only a name and a
 * specialty will be recommended - but will lose the points that come
 * from focus areas, experience, same-day availability and emergency
 * cover, and will sit below the seeded sample doctors. The hints under
 * each field say so, because "why is my doctor never shown?" is
 * otherwise invisible.
 */

const EMPTY_DOCTOR = {
  full_name: "",
  gender: "",
  email: "",
  phone: "",
  specialty: "",
  qualification: "",
  experience_years: "",
  focus_areas: "",
  consultation_fee: "",
  languages: "",
  available_days: "",
  next_available: "",
  area: "",
  handles_emergencies: null,
};


// Same list the patient's own Medical Reports page offers, so a
// report a hospital uploads shows up with the same icon and label
// once the patient looks at it.
const REPORT_TYPES = [
  { value: "cbc", label: "CBC" },
  { value: "blood", label: "Blood Test" },
  { value: "lipid", label: "Lipid Profile" },
  { value: "diabetes", label: "Diabetes" },
  { value: "liver", label: "Liver Function" },
  { value: "kidney", label: "Kidney Function" },
  { value: "thyroid", label: "Thyroid" },
  { value: "urine", label: "Urine Test" },
  { value: "vitamin", label: "Vitamin Test" },
  { value: "hormone", label: "Hormone Test" },
  { value: "imaging", label: "Imaging" },
  { value: "pathology", label: "Pathology" },
  { value: "cardiac", label: "Cardiac" },
  { value: "other", label: "Other" },
];


const EMPTY_UPLOAD = {
  report_name: "",
  report_type: "",
  staff_name: "",
  file: null,
};


function HospitalDashboard() {

  const [tab, setTab] = useState("doctors");

  const [profile, setProfile] = useState(null);
  const [options, setOptions] = useState(null);
  const [doctors, setDoctors] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_DOCTOR);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const [issued, setIssued] = useState(null);
  const [issuedFor, setIssuedFor] = useState("");


  // ==========================================
  // UPLOAD REPORTS (BY HEALTH ID)
  // ==========================================

  const [healthIdInput, setHealthIdInput] = useState("");
  const [lookupPatient, setLookupPatient] = useState(null);
  const [lookupError, setLookupError] = useState("");
  const [lookingUp, setLookingUp] = useState(false);

  const [uploadForm, setUploadForm] = useState(EMPTY_UPLOAD);
  const [uploadError, setUploadError] = useState("");
  const [uploading, setUploading] = useState(false);

  // What this hospital account has uploaded this session, most recent
  // first - not a stored patient history the hospital can browse, just
  // a receipt of what was just done, the way the mock-up's "Uploaded
  // this visit" list works.
  const [sessionUploads, setSessionUploads] = useState([]);


  // ==========================================
  // LOAD
  // ==========================================

  async function refresh() {

    try {

      const [profileData, optionsData, doctorData] = await Promise.all([
        getHospitalProfile(),
        getDoctorFormOptions(),
        getHospitalDoctors(),
      ]);

      setProfile(profileData);
      setOptions(optionsData);
      setDoctors(doctorData);
      setError("");

    } catch (error) {

      setError(error.message);

    } finally {

      setLoading(false);

    }
  }

  useEffect(() => {
    refresh();
  }, []);


  // ==========================================
  // ADD A DOCTOR
  // ==========================================

  function handleChange(event) {

    const { name, type, checked, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  }


  function openForm() {

    setForm({
      ...EMPTY_DOCTOR,
      // Most doctors sit at the hospital's own address, so start
      // there and let the rare branch case override it.
      area: profile?.area || "",
      handles_emergencies: Boolean(profile?.emergency_services),
    });

    setFormError("");
    setShowForm(true);
  }


  async function handleAdd(event) {

    event.preventDefault();

    setFormError("");
    setSaving(true);

    try {

      const payload = {
        full_name: form.full_name,
        gender: form.gender || null,
        email: form.email,
        phone: form.phone || null,
        specialty: form.specialty,
        qualification: form.qualification || null,
        experience_years:
          form.experience_years === "" ? 0 : Number(form.experience_years),
        focus_areas: form.focus_areas || null,
        consultation_fee:
          form.consultation_fee === "" ? null : Number(form.consultation_fee),
        languages: form.languages || null,
        available_days: form.available_days || null,
        next_available: form.next_available || null,
        area: form.area || null,
        handles_emergencies: Boolean(form.handles_emergencies),
      };

      const result = await addDoctor(payload);

      setIssued(result.credentials);
      setIssuedFor(result.doctor.full_name);

      setShowForm(false);
      setForm(EMPTY_DOCTOR);

      refresh();

    } catch (error) {

      setFormError(error.message);

    } finally {

      setSaving(false);

    }
  }


  // ==========================================
  // ROW ACTIONS
  // ==========================================

  async function handleReset(doctor) {

    const ok = window.confirm(
      `Issue a new temporary password for ${doctor.full_name}? ` +
      "Their current one stops working immediately."
    );

    if (!ok) {
      return;
    }

    try {

      const credentials = await resetDoctorPassword(doctor.id);

      setIssued(credentials);
      setIssuedFor(doctor.full_name);

      refresh();

    } catch (error) {

      setError(error.message);

    }
  }


  async function handleRemove(doctor) {

    const ok = window.confirm(
      `Remove ${doctor.full_name} from ${profile?.name}? ` +
      "Their login is deleted and they stop appearing in patient " +
      "recommendations straight away."
    );

    if (!ok) {
      return;
    }

    try {

      await deleteDoctor(doctor.id);
      refresh();

    } catch (error) {

      setError(error.message);

    }
  }


  // ==========================================
  // UPLOAD REPORTS (BY HEALTH ID)
  // ==========================================

  function resetPatientLookup() {
    setHealthIdInput("");
    setLookupPatient(null);
    setLookupError("");
    setUploadForm(EMPTY_UPLOAD);
    setUploadError("");
  }


  async function handleLookup(event) {

    event.preventDefault();

    setLookupError("");
    setLookupPatient(null);

    const cleaned = healthIdInput.replace(/\D/g, "");

    if (cleaned.length < 6) {
      setLookupError("Enter the full Health ID.");
      return;
    }

    setLookingUp(true);

    try {

      const patient = await lookupPatientByHealthId(cleaned);
      setLookupPatient(patient);

    } catch (error) {

      setLookupError(error.message);

    } finally {

      setLookingUp(false);

    }
  }


  function handleUploadFormChange(event) {

    const { name, value, files } = event.target;

    setUploadForm((current) => ({
      ...current,
      [name]: files ? files[0] : value,
    }));
  }


  async function handleUploadForPatient(event) {

    event.preventDefault();

    setUploadError("");

    if (!uploadForm.file) {
      setUploadError("Choose a report file to upload.");
      return;
    }

    if (!uploadForm.report_type) {
      setUploadError("Choose a report type.");
      return;
    }

    setUploading(true);

    try {

      const formData = new FormData();

      formData.append(
        "report_name",
        uploadForm.report_name.trim() || uploadForm.file.name
      );
      formData.append("report_type", uploadForm.report_type);
      formData.append("staff_name", uploadForm.staff_name.trim());
      formData.append("file", uploadForm.file);

      const result = await uploadReportForPatient(
        lookupPatient.health_id,
        formData
      );

      setSessionUploads((current) => [result, ...current]);

      // Ready for the next file for the same patient - stay on their
      // record rather than clearing the whole lookup, since staff
      // often have more than one document per visit.
      setUploadForm(EMPTY_UPLOAD);

    } catch (error) {

      setUploadError(error.message);

    } finally {

      setUploading(false);

    }
  }


  // ==========================================
  // RENDER
  // ==========================================

  if (loading) {

    return (

      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <p>Loading your hospital…</p>
      </div>

    );
  }

  return (

    <div className="portal-page">

      <PortalNav
        role="hospital"
        subtitle={profile?.name}
        active={tab}
        onSelect={setTab}
        items={[
          { key: "doctors", label: `Doctors (${doctors.length})`, icon: "doctor" },
          { key: "overview", label: "Hospital details", icon: "hospital" },
          { key: "upload", label: "Upload reports", icon: "upload" },
        ]}
      />

      <main className="portal-content">

        <div className="dashboard-header">

          <h1>{profile?.name}</h1>

          <p>
            {[profile?.hospital_type, profile?.area, profile?.city]
              .filter(Boolean)
              .join(" · ")}
          </p>

        </div>

        {error && (
          <div className="error-message">{error}</div>
        )}

        {issued && (
          <CredentialsCard
            title={`Sign-in details for ${issuedFor}`}
            credentials={issued}
            onDone={() => setIssued(null)}
          />
        )}


        {/* ====================================
            TABS
        ==================================== */}


        {/* ====================================
            OVERVIEW
        ==================================== */}

        {tab === "overview" && profile && (

          <div className="dashboard-card info-block">

            <h3>Registered details</h3>

            <p className="info-block-note">
              These were entered by the platform administrator. Ask
              them to update anything that has changed.
            </p>

            <div className="info-grid">

              <div className="info-item">
                <span>Hospital ID</span>
                <strong className="mono">{profile.login_id}</strong>
              </div>

              <div className="info-item">
                <span>Type</span>
                <strong>{profile.hospital_type || "—"}</strong>
              </div>

              <div className="info-item">
                <span>Registration</span>
                <strong>{profile.registration_number || "—"}</strong>
              </div>

              <div className="info-item">
                <span>Beds</span>
                <strong>{profile.bed_count ?? "—"}</strong>
              </div>

              <div className="info-item">
                <span>Address</span>
                <strong>{profile.address || "—"}</strong>
              </div>

              <div className="info-item">
                <span>Area</span>
                <strong>{profile.area || "—"}</strong>
              </div>

              <div className="info-item">
                <span>City</span>
                <strong>{profile.city || "—"}</strong>
              </div>

              <div className="info-item">
                <span>PIN code</span>
                <strong>{profile.pincode || "—"}</strong>
              </div>

              <div className="info-item">
                <span>Email</span>
                <strong>{profile.email || "—"}</strong>
              </div>

              <div className="info-item">
                <span>Phone</span>
                <strong>{profile.phone || "—"}</strong>
              </div>

              <div className="info-item">
                <span>Contact person</span>
                <strong>{profile.contact_person || "—"}</strong>
              </div>

              <div className="info-item">
                <span>Emergency department</span>
                <strong>
                  {profile.emergency_services ? "24x7" : "No"}
                </strong>
              </div>

            </div>

          </div>

        )}


        {/* ====================================
            UPLOAD REPORTS (BY HEALTH ID)
        ==================================== */}

        {tab === "upload" && (

          <>

            <div className="portal-section-head">
              <h2>Upload a report to a patient's account</h2>
            </div>

            <div className="dashboard-card">

              <h3 className="form-section-title">Find the patient</h3>

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
                      Ask the patient for the Health ID on their card
                      or their dashboard, or read it off their QR code.
                    </p>
                  </div>

                </div>

                <div className="form-actions">
                  <button
                    className="primary-btn"
                    type="submit"
                    disabled={lookingUp}
                  >
                    {lookingUp ? "Looking up…" : "Find patient"}
                  </button>

                  {lookupPatient && (
                    <button
                      className="secondary-btn"
                      type="button"
                      onClick={resetPatientLookup}
                    >
                      Clear
                    </button>
                  )}
                </div>

              </form>

            </div>


            {lookupPatient && (

              <div className="dashboard-card">

                <h3 className="form-section-title">
                  Uploading for {lookupPatient.full_name}
                </h3>

                <p className="portal-note">
                  {[
                    lookupPatient.age ? `${lookupPatient.age} years` : null,
                    lookupPatient.gender,
                  ]
                    .filter(Boolean)
                    .join(" · ") || "Confirm this is the right patient before uploading."}
                  {" "}
                  <span className="mono">{lookupPatient.health_id}</span>
                </p>

                <form onSubmit={handleUploadForPatient}>

                  {uploadError && (
                    <div className="error-message">{uploadError}</div>
                  )}

                  <div className="form-row">

                    <div className="form-group">
                      <label>Report name</label>
                      <input
                        className="form-input"
                        name="report_name"
                        value={uploadForm.report_name}
                        onChange={handleUploadFormChange}
                        placeholder="e.g. Comprehensive metabolic panel"
                      />
                    </div>

                    <div className="form-group">
                      <label>Report type</label>
                      <select
                        className="form-select"
                        name="report_type"
                        value={uploadForm.report_type}
                        onChange={handleUploadFormChange}
                      >
                        <option value="">Choose one</option>
                        {REPORT_TYPES.map((type) => (
                          <option key={type.value} value={type.value}>
                            {type.label}
                          </option>
                        ))}
                      </select>
                    </div>

                  </div>

                  <div className="form-group">
                    <label>Your name (recorded for the audit trail)</label>
                    <input
                      className="form-input"
                      name="staff_name"
                      value={uploadForm.staff_name}
                      onChange={handleUploadFormChange}
                      placeholder="e.g. R. Fernandes"
                    />
                    <p className="field-hint">
                      No separate staff login is needed - your name is
                      stored against this upload so the patient can see
                      who added it.
                    </p>
                  </div>

                  <div className="form-group">
                    <label>Report file (PDF)</label>
                    <input
                      className="form-input"
                      type="file"
                      name="file"
                      accept="application/pdf"
                      onChange={handleUploadFormChange}
                    />
                  </div>

                  <div className="form-actions">
                    <button
                      className="primary-btn"
                      type="submit"
                      disabled={uploading}
                    >
                      {uploading ? "Uploading…" : "Upload to this patient"}
                    </button>
                  </div>

                </form>

              </div>

            )}


            {sessionUploads.length > 0 && (

              <div className="dashboard-card">

                <h3 className="form-section-title">Uploaded this session</h3>

                <div className="entity-list">

                  {sessionUploads.map((upload) => (

                    <div className="entity-card" key={upload.id}>

                      <div className="entity-main">

                        <div className="entity-title-row">
                          <h3>{upload.report_name}</h3>
                          <span className="pill pill-specialty">
                            {upload.patient_full_name}
                          </span>
                          {upload.status === "summarized" ? (
                            <span className="pill pill-ok">Processed</span>
                          ) : upload.status === "failed" ? (
                            <span className="pill pill-warn">
                              Needs a retry
                            </span>
                          ) : (
                            <span className="pill pill-warn">Processing</span>
                          )}
                        </div>

                        <p className="entity-sub">
                          Recorded by{" "}
                          {upload.uploaded_by_staff || "front desk"} ·{" "}
                          {upload.patient_health_id}
                        </p>

                      </div>

                    </div>

                  ))}

                </div>

              </div>

            )}

          </>

        )}


        {/* ====================================
            DOCTORS
        ==================================== */}

        {tab === "doctors" && (

          <>

            <div className="portal-section-head">

              <h2>
                {doctors.length === 0
                  ? "No doctors yet"
                  : `${doctors.length} doctor${doctors.length === 1 ? "" : "s"}`}
              </h2>

              <button
                className="primary-btn compact-btn"
                onClick={() => (showForm ? setShowForm(false) : openForm())}
              >
                {showForm ? "Cancel" : "Add a doctor"}
              </button>

            </div>


            {showForm && (

              <div className="dashboard-card">

                <form onSubmit={handleAdd}>

                  {formError && (
                    <div className="error-message">{formError}</div>
                  )}

                  <h3 className="form-section-title">Who they are</h3>

                  <div className="form-row">

                    <div className="form-group">
                      <label>Full name</label>
                      <input
                        className="form-input"
                        name="full_name"
                        value={form.full_name}
                        onChange={handleChange}
                        placeholder="Dr. Anjali Rao"
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label>Gender</label>
                      <select
                        className="form-select"
                        name="gender"
                        value={form.gender}
                        onChange={handleChange}
                      >
                        <option value="">Prefer not to say</option>
                        {(options?.genders || []).map((item) => (
                          <option key={item} value={item}>{item}</option>
                        ))}
                      </select>
                    </div>

                  </div>

                  <div className="form-row">

                    <div className="form-group">
                      <label>Email</label>
                      <input
                        className="form-input"
                        type="email"
                        name="email"
                        value={form.email}
                        onChange={handleChange}
                        placeholder="anjali.rao@hospital.in"
                        required
                      />
                      <p className="field-hint">
                        Identifies the account. They sign in with the
                        ID you're about to be given, not this.
                      </p>
                    </div>

                    <div className="form-group">
                      <label>Phone</label>
                      <input
                        className="form-input"
                        name="phone"
                        value={form.phone}
                        onChange={handleChange}
                        placeholder="98490 00000"
                      />
                    </div>

                  </div>


                  <h3 className="form-section-title">What they practise</h3>

                  <div className="form-row">

                    <div className="form-group">
                      <label>Specialty</label>
                      <select
                        className="form-select"
                        name="specialty"
                        value={form.specialty}
                        onChange={handleChange}
                        required
                      >
                        <option value="">Select a specialty…</option>
                        {(options?.specialties || []).map((item) => (
                          <option key={item} value={item}>{item}</option>
                        ))}
                      </select>
                      <p className="field-hint">
                        The single biggest factor in whether a patient
                        is shown this doctor.
                      </p>
                    </div>

                    <div className="form-group">
                      <label>Years in practice</label>
                      <input
                        className="form-input"
                        type="number"
                        min="0"
                        max="70"
                        name="experience_years"
                        value={form.experience_years}
                        onChange={handleChange}
                        placeholder="12"
                      />
                    </div>

                  </div>

                  <div className="form-group">
                    <label>Qualifications</label>
                    <input
                      className="form-input"
                      name="qualification"
                      value={form.qualification}
                      onChange={handleChange}
                      placeholder="MBBS, MD (General Medicine)"
                    />
                  </div>

                  <div className="form-group">
                    <label>Conditions they handle</label>
                    <input
                      className="form-input"
                      name="focus_areas"
                      value={form.focus_areas}
                      onChange={handleChange}
                      placeholder="chest pain, palpitations, blood pressure, cholesterol"
                    />
                    <p className="field-hint">
                      Comma separated, in the words a patient would
                      use. These are matched against what the patient
                      typed, so "chest pain" earns a match and
                      "cardiovascular pathology" does not.
                    </p>
                  </div>

                  <div className="form-row">

                    <div className="form-group">
                      <label>Consultation fee (₹)</label>
                      <input
                        className="form-input"
                        type="number"
                        min="0"
                        name="consultation_fee"
                        value={form.consultation_fee}
                        onChange={handleChange}
                        placeholder="600"
                      />
                    </div>

                    <div className="form-group">
                      <label>Languages</label>
                      <input
                        className="form-input"
                        name="languages"
                        value={form.languages}
                        onChange={handleChange}
                        placeholder="Telugu, Hindi, English"
                      />
                      <p className="field-hint">
                        Comma separated.
                        {options?.common_languages
                          ? ` Common here: ${options.common_languages
                              .slice(0, 4)
                              .join(", ")}.`
                          : ""}
                      </p>
                    </div>

                  </div>


                  <h3 className="form-section-title">When and where</h3>

                  <div className="form-row">

                    <div className="form-group">
                      <label>Days available</label>
                      <input
                        className="form-input"
                        name="available_days"
                        value={form.available_days}
                        onChange={handleChange}
                        placeholder="Mon-Sat"
                      />
                    </div>

                    <div className="form-group">
                      <label>Next free slot</label>
                      <input
                        className="form-input"
                        name="next_available"
                        value={form.next_available}
                        onChange={handleChange}
                        placeholder="Today, 6:30 PM"
                      />
                      <p className="field-hint">
                        A slot starting with "Today" scores extra for
                        patients who need to be seen quickly. Keep it
                        current or drop it.
                      </p>
                    </div>

                  </div>

                  <div className="form-group">
                    <label>Area</label>
                    <select
                      className="form-select"
                      name="area"
                      value={form.area}
                      onChange={handleChange}
                    >
                      <option value="">
                        Same as the hospital{profile?.area ? ` (${profile.area})` : ""}
                      </option>
                      {(options?.areas || []).map((area) => (
                        <option key={area} value={area}>{area}</option>
                      ))}
                    </select>
                    <p className="field-hint">
                      Only change this for a doctor who sits at a
                      different branch. It sets how far away patients
                      are told this doctor is.
                    </p>
                  </div>

                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      name="handles_emergencies"
                      checked={Boolean(form.handles_emergencies)}
                      onChange={handleChange}
                    />
                    <span>
                      Available for emergencies. Moves this doctor up
                      for patients who describe something urgent.
                    </span>
                  </label>

                  <p className="portal-note">
                    Ratings aren't on this form. They come from patient
                    feedback once it exists, so a new doctor starts
                    without them.
                  </p>

                  <div className="form-actions">

                    <button
                      className="secondary-btn"
                      type="button"
                      onClick={() => setShowForm(false)}
                    >
                      Cancel
                    </button>

                    <button
                      className="primary-btn"
                      type="submit"
                      disabled={saving}
                    >
                      {saving ? "Adding…" : "Add doctor"}
                    </button>

                  </div>

                </form>

              </div>

            )}


            {doctors.length === 0 && !showForm && (

              <div className="dashboard-card empty-state">
                <p>
                  Add your first doctor and they'll start appearing in
                  patient recommendations right away.
                </p>
              </div>

            )}


            <div className="entity-list">

              {doctors.map((doctor) => (

                <div className="entity-card" key={doctor.id}>

                  <div className="entity-main">

                    <div className="entity-title-row">

                      <h3>{doctor.full_name}</h3>

                      <span className="pill pill-specialty">
                        {doctor.specialty}
                      </span>

                      {doctor.password_pending && (
                        <span className="pill pill-warn">
                          Hasn't signed in yet
                        </span>
                      )}

                      {doctor.handles_emergencies && (
                        <span className="pill pill-ok">Emergencies</span>
                      )}

                    </div>

                    <p className="entity-sub">
                      {[
                        doctor.qualification,
                        doctor.experience_years
                          ? `${doctor.experience_years} years`
                          : null,
                        doctor.area,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>

                    <div className="entity-facts">

                      <div className="entity-fact">
                        <span>ID</span>
                        <strong className="mono">
                          {doctor.login_id || "—"}
                        </strong>
                      </div>

                      <div className="entity-fact">
                        <span>Email</span>
                        <strong>{doctor.email || "—"}</strong>
                      </div>

                      <div className="entity-fact">
                        <span>Phone</span>
                        <strong>{doctor.phone || "—"}</strong>
                      </div>

                      <div className="entity-fact">
                        <span>Fee</span>
                        <strong>
                          {doctor.consultation_fee != null
                            ? `₹${doctor.consultation_fee}`
                            : "—"}
                        </strong>
                      </div>

                      <div className="entity-fact">
                        <span>Days</span>
                        <strong>{doctor.available_days || "—"}</strong>
                      </div>

                      <div className="entity-fact">
                        <span>Next slot</span>
                        <strong>{doctor.next_available || "—"}</strong>
                      </div>

                    </div>

                    {doctor.focus_areas && (
                      <p className="entity-focus">
                        Handles: {doctor.focus_areas}
                      </p>
                    )}

                  </div>

                  <div className="entity-actions">

                    <button
                      className="link-btn"
                      onClick={() => handleReset(doctor)}
                    >
                      Reissue password
                    </button>

                    <button
                      className="link-btn danger-link"
                      onClick={() => handleRemove(doctor)}
                    >
                      Remove
                    </button>

                  </div>

                </div>

              ))}

            </div>

          </>

        )}

      </main>

    </div>
  );
}

export default HospitalDashboard;
