import { useEffect, useState } from "react";

import PortalNav from "../components/PortalNav";
import Icon from "../components/Icon";
import CredentialsCard from "../components/CredentialsCard";
import LedgerIntegrityCard from "../components/LedgerIntegrityCard";

import {
  getAdminOptions,
  getAdminStats,
  getHospitals,
  createHospital,
  resetHospitalPassword,
  setHospitalActive,
  deleteHospital,
} from "../services/portalApi";

/**
 * AdminDashboard
 * ------------------------------------------------------------
 * The admin does one thing: bring hospitals onto the platform. Fill in
 * the hospital's details, and the server returns an ID and a
 * temporary password to hand to whoever runs it.
 *
 * Deliberately not here: doctors. A hospital adds its own, from its
 * own portal. The admin never sees a doctor list, because the moment
 * an admin can add a doctor to someone else's hospital, "who is
 * accountable for this doctor's record" stops having one answer.
 */

const EMPTY_FORM = {
  name: "",
  registration_number: "",
  hospital_type: "",
  address: "",
  area: "",
  city: "Hyderabad",
  pincode: "",
  phone: "",
  email: "",
  contact_person: "",
  contact_phone: "",
  bed_count: "",
  emergency_services: false,
};


function AdminDashboard() {

  const [options, setOptions] = useState(null);
  const [stats, setStats] = useState(null);
  const [hospitals, setHospitals] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [view, setView] = useState("overview");
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  // Set once, right after an account is issued or reissued. Nothing
  // reads the password back afterwards, so this is the only copy.
  const [issued, setIssued] = useState(null);
  const [issuedFor, setIssuedFor] = useState("");


  // ==========================================
  // LOAD
  // ==========================================

  async function refresh() {

    try {

      const [optionsData, statsData, hospitalData] = await Promise.all([
        getAdminOptions(),
        getAdminStats(),
        getHospitals(),
      ]);

      setOptions(optionsData);
      setStats(statsData);
      setHospitals(hospitalData);
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
  // CREATE
  // ==========================================

  function handleChange(event) {

    const { name, type, checked, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: type === "checkbox" ? checked : value,
    }));
  }


  async function handleCreate(event) {

    event.preventDefault();

    setFormError("");
    setSaving(true);

    try {

      const payload = {
        ...form,
        // Empty optional text fields go as null rather than "", so the
        // database holds "not given" instead of "given as blank".
        registration_number: form.registration_number || null,
        hospital_type: form.hospital_type || null,
        address: form.address || null,
        pincode: form.pincode || null,
        phone: form.phone || null,
        contact_person: form.contact_person || null,
        contact_phone: form.contact_phone || null,
        bed_count: form.bed_count === "" ? null : Number(form.bed_count),
      };

      const result = await createHospital(payload);

      setIssued(result.credentials);
      setIssuedFor(result.hospital.name);

      setForm(EMPTY_FORM);
      setShowForm(false);
      setView("hospitals");

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

  async function handleReset(hospital) {

    const ok = window.confirm(
      `Issue a new temporary password for ${hospital.name}? ` +
      "Their current password stops working immediately."
    );

    if (!ok) {
      return;
    }

    try {

      const credentials = await resetHospitalPassword(hospital.id);

      setIssued(credentials);
      setIssuedFor(hospital.name);

      refresh();

    } catch (error) {

      setError(error.message);

    }
  }


  async function handleToggleActive(hospital) {

    const turningOff = hospital.is_active;

    if (turningOff) {

      const ok = window.confirm(
        `Deactivate ${hospital.name}? Its login and all ${hospital.doctor_count} ` +
        "of its doctors' logins stop working, and those doctors stop " +
        "appearing in patient recommendations. Nothing is deleted."
      );

      if (!ok) {
        return;
      }
    }

    try {

      await setHospitalActive(hospital.id, !hospital.is_active);
      refresh();

    } catch (error) {

      setError(error.message);

    }
  }


  async function handleDelete(hospital) {

    const ok = window.confirm(
      `Permanently delete ${hospital.name}, its ${hospital.doctor_count} ` +
      "doctors and all of their logins? This cannot be undone - " +
      "deactivate instead if the hospital has actually been in use."
    );

    if (!ok) {
      return;
    }

    try {

      await deleteHospital(hospital.id);
      refresh();

    } catch (error) {

      setError(error.message);

    }
  }


  // ==========================================
  // RENDER
  // ==========================================

  if (loading) {

    return (

      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <p>Loading the platform…</p>
      </div>

    );
  }

  // ---- derived for the views
  const awaiting = hospitals.filter(
    (h) => h.is_active && !h.password_changed
  );
  const deactivated = hospitals.filter((h) => !h.is_active);

  const needle = query.trim().toLowerCase();

  const visible = hospitals.filter((h) => {

    if (statusFilter === "active" && !h.is_active) return false;
    if (statusFilter === "deactivated" && h.is_active) return false;
    if (statusFilter === "awaiting" && !(h.is_active && !h.password_changed)) return false;

    if (!needle) return true;

    return [h.name, h.login_id, h.area, h.city, h.hospital_type, h.email]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
      .includes(needle);
  });

  function openForm() {
    setView("hospitals");
    setShowForm(true);
    setFormError("");
  }

  function closeForm() {
    setShowForm(false);
    setFormError("");
  }

  function statusPills(hospital) {
    return (
      <>
        {!hospital.is_active && (
          <span className="pill pill-muted">Deactivated</span>
        )}
        {hospital.is_active && !hospital.password_changed && (
          <span className="pill pill-warn">Not signed in yet</span>
        )}
        {hospital.is_active && hospital.password_changed && (
          <span className="pill pill-ok">Active</span>
        )}
      </>
    );
  }

  const titles = {
    overview: ["Overview", "How the platform is doing right now."],
    hospitals: [
      "Hospitals",
      "Add a hospital, hand over the ID and password that comes back, and they add their own doctors from there.",
    ],
    ledger: [
      "Consent ledger",
      "Every approval and revocation is recorded in a tamper-evident chain. Check it here.",
    ],
  };

  return (

    <div className="portal-page">

      <PortalNav
        role="admin"
        subtitle="Platform administration"
        active={view}
        onSelect={setView}
        items={[
          { key: "overview", label: "Overview", icon: "grid" },
          { key: "hospitals", label: `Hospitals (${hospitals.length})`, icon: "hospital" },
          { key: "ledger", label: "Consent ledger", icon: "chain" },
        ]}
      />

      <main className="portal-content">

        <header className="page-head">

          <div>
            <h1>{titles[view][0]}</h1>
            <p>{titles[view][1]}</p>
          </div>

          {view !== "ledger" && (
            <div className="page-actions">
              <button className="primary-btn" onClick={openForm}>
                <Icon name="plus" size={18} />
                Add a hospital
              </button>
            </div>
          )}

        </header>


        {error && (
          <div className="error-message" role="alert">{error}</div>
        )}


        {/* credentials are shown once, on whichever view you are on */}
        {issued && (
          <CredentialsCard
            title={`Sign-in details for ${issuedFor}`}
            credentials={issued}
            onDone={() => setIssued(null)}
          />
        )}


        {/* ====================================
            OVERVIEW
        ==================================== */}

        {view === "overview" && (

          <>

            {stats && (

              <div className="stat-strip">

                <div className="stat-tile">
                  <span className="stat-icon"><Icon name="hospital" size={20} /></span>
                  <span className="stat-number">{stats.hospitals}</span>
                  <span className="stat-label">Hospitals</span>
                </div>

                <div className="stat-tile">
                  <span className="stat-icon"><Icon name="doctor" size={20} /></span>
                  <span className="stat-number">{stats.doctors}</span>
                  <span className="stat-label">Doctors listed</span>
                </div>

                <div className="stat-tile">
                  <span className="stat-icon"><Icon name="users" size={20} /></span>
                  <span className="stat-number">{stats.patients}</span>
                  <span className="stat-label">Patients</span>
                </div>

                <div className="stat-tile">
                  <span className="stat-icon"><Icon name="file" size={20} /></span>
                  <span className="stat-number">{stats.sample_doctors}</span>
                  <span className="stat-label">Sample doctor rows</span>
                </div>

              </div>

            )}

            {stats && stats.sample_doctors > 0 && (

              <p className="portal-note">
                {stats.sample_doctors} of the doctors being recommended to
                patients are seeded sample records with no hospital behind
                them. They disappear from the recommendations as soon as
                they are removed from the database, and real hospital
                doctors are ranked by the same rules.
              </p>

            )}

            <div className="admin-split">

              <section className="panel">

                <div className="panel-head">
                  <h2>Needs attention</h2>
                  <span className="panel-count">
                    {awaiting.length + deactivated.length}
                  </span>
                </div>

                {awaiting.length + deactivated.length === 0 ? (
                  <p className="panel-empty">
                    <Icon name="check" size={18} />
                    Every hospital is active and has signed in.
                  </p>
                ) : (
                  <ul className="attention-list">
                    {awaiting.map((h) => (
                      <li key={"a" + h.id}>
                        <Icon name="alert" size={18} />
                        <span>
                          <strong>{h.name}</strong>
                          <small>
                            Has not signed in yet. Login ID{" "}
                            <span className="mono">{h.login_id}</span>
                          </small>
                        </span>
                        <button
                          className="mini-btn"
                          onClick={() => handleReset(h)}
                        >
                          Reissue password
                        </button>
                      </li>
                    ))}
                    {deactivated.map((h) => (
                      <li key={"d" + h.id}>
                        <Icon name="lock" size={18} />
                        <span>
                          <strong>{h.name}</strong>
                          <small>Deactivated. Its doctors cannot sign in.</small>
                        </span>
                        <button
                          className="mini-btn"
                          onClick={() => handleToggleActive(h)}
                        >
                          Reactivate
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

              </section>

              <section className="panel">

                <div className="panel-head">
                  <h2>Hospitals by doctors</h2>
                  <button className="link-btn" onClick={() => setView("hospitals")}>
                    View all
                  </button>
                </div>

                {hospitals.length === 0 ? (
                  <p className="panel-empty">
                    Nothing here yet. Add the first hospital and it can start
                    listing its doctors straight away.
                  </p>
                ) : (
                  <ul className="bar-list">
                    {[...hospitals]
                      .sort((a, b) => b.doctor_count - a.doctor_count)
                      .slice(0, 6)
                      .map((h) => {
                        const max = Math.max(
                          1,
                          ...hospitals.map((x) => x.doctor_count)
                        );
                        return (
                          <li key={h.id}>
                            <span className="bar-label">{h.name}</span>
                            <span className="bar-track">
                              <span
                                className="bar-fill"
                                style={{ width: `${(h.doctor_count / max) * 100}%` }}
                              />
                            </span>
                            <span className="bar-value">{h.doctor_count}</span>
                          </li>
                        );
                      })}
                  </ul>
                )}

              </section>

            </div>

          </>

        )}


        {/* ====================================
            HOSPITALS
        ==================================== */}

        {view === "hospitals" && (

          <section className="panel panel-flush">

            <div className="toolbar">

              <label className="search-field">
                <Icon name="search" size={18} />
                <input
                  type="search"
                  placeholder="Search name, ID, area or email"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  aria-label="Search hospitals"
                />
              </label>

              <div className="trends-filter" role="group" aria-label="Filter by status">
                {[
                  ["all", "All"],
                  ["active", "Active"],
                  ["awaiting", "Not signed in"],
                  ["deactivated", "Deactivated"],
                ].map(([key, label]) => (
                  <button
                    key={key}
                    className={statusFilter === key ? "active" : ""}
                    onClick={() => setStatusFilter(key)}
                  >
                    {label}
                  </button>
                ))}
              </div>

            </div>

            {hospitals.length === 0 ? (

              <p className="panel-empty panel-empty-pad">
                Nothing here yet. Add the first hospital and it can start
                listing its doctors straight away.
              </p>

            ) : visible.length === 0 ? (

              <p className="panel-empty panel-empty-pad">
                No hospital matches that search.
              </p>

            ) : (

              <div className="table-wrap">

                <table className="data-table">

                  <thead>
                    <tr>
                      <th>Hospital</th>
                      <th>Login ID</th>
                      <th className="num">Doctors</th>
                      <th className="num hide-sm">Beds</th>
                      <th className="hide-md">Contact</th>
                      <th>Status</th>
                      <th aria-label="Actions"></th>
                    </tr>
                  </thead>

                  <tbody>

                    {visible.map((hospital) => (

                      <tr
                        key={hospital.id}
                        className={hospital.is_active ? "" : "is-muted"}
                      >

                        <td>
                          <div className="cell-title">{hospital.name}</div>
                          <div className="cell-sub">
                            {[hospital.hospital_type, hospital.area, hospital.city]
                              .filter(Boolean)
                              .join(" · ")}
                          </div>
                          {hospital.registration_number && (
                            <div className="cell-sub mono">
                              {hospital.registration_number}
                            </div>
                          )}
                        </td>

                        <td className="mono">{hospital.login_id}</td>

                        <td className="num">{hospital.doctor_count}</td>

                        <td className="num hide-sm">
                          {hospital.bed_count != null ? hospital.bed_count : "—"}
                        </td>

                        <td className="hide-md">
                          <div>{hospital.email || "—"}</div>
                          <div className="cell-sub">{hospital.phone || ""}</div>
                        </td>

                        <td>
                          <div className="pill-stack">
                            {statusPills(hospital)}
                            {hospital.emergency_services && (
                              <span className="pill pill-specialty">24x7 ER</span>
                            )}
                          </div>
                        </td>

                        <td>
                          <div className="row-actions">
                            <button
                              className="mini-btn"
                              onClick={() => handleReset(hospital)}
                            >
                              Reissue password
                            </button>
                            <button
                              className="mini-btn"
                              onClick={() => handleToggleActive(hospital)}
                            >
                              {hospital.is_active ? "Deactivate" : "Reactivate"}
                            </button>
                            <button
                              className="mini-btn mini-btn-danger"
                              onClick={() => handleDelete(hospital)}
                            >
                              Delete
                            </button>
                          </div>
                        </td>

                      </tr>

                    ))}

                  </tbody>

                </table>

              </div>

            )}

          </section>

        )}


        {/* ====================================
            CONSENT LEDGER
        ==================================== */}

        {view === "ledger" && <LedgerIntegrityCard />}

      </main>


      {/* ====================================
          ADD A HOSPITAL (slides in from the right)
      ==================================== */}

      {showForm && (

        <div className="drawer-root" role="dialog" aria-modal="true" aria-label="Add a hospital">

          <div className="drawer-scrim" onClick={closeForm} />

          <aside className="drawer">

            <div className="drawer-head">
              <div>
                <h2>Add a hospital</h2>
                <p>You get a login ID and a one-time password to hand over.</p>
              </div>
              <button
                className="drawer-close"
                onClick={closeForm}
                aria-label="Close"
              >
                <Icon name="close" size={20} />
              </button>
            </div>

            <div className="drawer-body">

            <form onSubmit={handleCreate}>

              {formError && (
                <div className="error-message">{formError}</div>
              )}

              <h3 className="form-section-title">The hospital</h3>

              <div className="form-row">

                <div className="form-group">
                  <label>Hospital name</label>
                  <input
                    className="form-input"
                    name="name"
                    value={form.name}
                    onChange={handleChange}
                    placeholder="Sunrise Multispeciality Hospital"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Type</label>
                  <select
                    className="form-select"
                    name="hospital_type"
                    value={form.hospital_type}
                    onChange={handleChange}
                  >
                    <option value="">Select…</option>
                    {(options?.hospital_types || []).map((item) => (
                      <option key={item} value={item}>{item}</option>
                    ))}
                  </select>
                </div>

              </div>

              <div className="form-row">

                <div className="form-group">
                  <label>Registration number</label>
                  <input
                    className="form-input"
                    name="registration_number"
                    value={form.registration_number}
                    onChange={handleChange}
                    placeholder="TS/HOSP/2026/00123"
                  />
                </div>

                <div className="form-group">
                  <label>Beds</label>
                  <input
                    className="form-input"
                    type="number"
                    min="0"
                    name="bed_count"
                    value={form.bed_count}
                    onChange={handleChange}
                    placeholder="120"
                  />
                </div>

              </div>


              <h3 className="form-section-title">Where it is</h3>

              <div className="form-group">
                <label>Address</label>
                <input
                  className="form-input"
                  name="address"
                  value={form.address}
                  onChange={handleChange}
                  placeholder="Plot 14, Road No. 2"
                />
              </div>

              <div className="form-row form-row-triple">

                <div className="form-group">
                  <label>Area</label>
                  <select
                    className="form-select"
                    name="area"
                    value={form.area}
                    onChange={handleChange}
                    required
                  >
                    <option value="">Select an area…</option>
                    {(options?.areas || []).map((area) => (
                      <option key={area} value={area}>{area}</option>
                    ))}
                  </select>
                  <p className="field-hint">
                    Sets the map point every doctor here is measured
                    from when patients search nearby.
                  </p>
                </div>

                <div className="form-group">
                  <label>City</label>
                  <select
                    className="form-select"
                    name="city"
                    value={form.city}
                    onChange={handleChange}
                  >
                    {(options?.cities || ["Hyderabad"]).map((city) => (
                      <option key={city} value={city}>{city}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label>PIN code</label>
                  <input
                    className="form-input"
                    name="pincode"
                    value={form.pincode}
                    onChange={handleChange}
                    placeholder="500034"
                  />
                </div>

              </div>


              <h3 className="form-section-title">Who to reach</h3>

              <div className="form-row">

                <div className="form-group">
                  <label>Hospital email</label>
                  <input
                    className="form-input"
                    type="email"
                    name="email"
                    value={form.email}
                    onChange={handleChange}
                    placeholder="admin@sunrisehospital.in"
                    required
                  />
                  <p className="field-hint">
                    Used to identify the account. They sign in with
                    the ID, not this.
                  </p>
                </div>

                <div className="form-group">
                  <label>Hospital phone</label>
                  <input
                    className="form-input"
                    name="phone"
                    value={form.phone}
                    onChange={handleChange}
                    placeholder="040 2345 6789"
                  />
                </div>

              </div>

              <div className="form-row">

                <div className="form-group">
                  <label>Contact person</label>
                  <input
                    className="form-input"
                    name="contact_person"
                    value={form.contact_person}
                    onChange={handleChange}
                    placeholder="Dr. Meera Prasad"
                  />
                </div>

                <div className="form-group">
                  <label>Their phone</label>
                  <input
                    className="form-input"
                    name="contact_phone"
                    value={form.contact_phone}
                    onChange={handleChange}
                    placeholder="98490 00000"
                  />
                </div>

              </div>

              <label className="checkbox-row">
                <input
                  type="checkbox"
                  name="emergency_services"
                  checked={form.emergency_services}
                  onChange={handleChange}
                />
                <span>
                  Runs a 24x7 emergency department. Doctors added here
                  inherit this, and it moves them up for urgent cases.
                </span>
              </label>

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
                  {saving ? "Creating…" : "Create hospital"}
                </button>

              </div>

            </form>

            </div>

          </aside>

        </div>

      )}

    </div>
  );
}

export default AdminDashboard;
