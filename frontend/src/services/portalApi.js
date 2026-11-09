// ============================================================
// PORTAL API
// ============================================================
//
// Admin, hospital and doctor endpoints. Kept out of api.js on
// purpose: that file is the patient app, and nothing in here is
// reachable from a patient session.
//
// Login itself is NOT here - it is still loginUser() in api.js. The
// backend matches the value you type against email OR issued login ID,
// so the same call works for all four roles. What changed is the
// response, which now carries role / must_change_password /
// display_name so the client knows which portal to open.

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";


function authHeaders(extra = {}) {

  const token = localStorage.getItem("access_token");

  return {
    Authorization: `Bearer ${token}`,
    ...extra,
  };
}


// A 204 has no body, so response.json() would throw on every delete.
async function request(path, options = {}) {

  const response = await fetch(`${API_URL}${path}`, options);

  if (response.status === 204) {
    return null;
  }

  const text = await response.text();

  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {

    throw new Error(
      readError(data) ||
      "Something went wrong. Try again."
    );

  }

  return data;
}


// FastAPI returns `detail` as a string for our own HTTPExceptions, but
// as a list of field errors when validation fails. Showing "[object
// Object]" to someone filling in a form is not a helpful error.
function readError(data) {

  const detail = data?.detail;

  if (!detail) {
    return null;
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {

    return detail
      .map((item) => {

        const field = Array.isArray(item.loc)
          ? item.loc[item.loc.length - 1]
          : null;

        return field
          ? `${String(field).replace(/_/g, " ")}: ${item.msg}`
          : item.msg;

      })
      .join(", ");

  }

  return null;
}


// ============================================================
// ACCOUNT (any role)
// ============================================================

export async function getAccount() {

  return request("/auth/me", {
    headers: authHeaders(),
  });
}


export async function changePassword(currentPassword, newPassword) {

  return request("/auth/change-password", {
    method: "POST",

    headers: authHeaders({
      "Content-Type": "application/json",
    }),

    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}


// ============================================================
// ADMIN
// ============================================================

export async function getAdminOptions() {

  return request("/admin/options", {
    headers: authHeaders(),
  });
}


export async function getAdminStats() {

  return request("/admin/stats", {
    headers: authHeaders(),
  });
}


export async function getHospitals() {

  return request("/admin/hospitals", {
    headers: authHeaders(),
  });
}


// Returns { hospital, credentials }. The credentials are the only copy
// of the temporary password that will ever exist - show them, do not
// log them.
export async function createHospital(hospitalData) {

  return request("/admin/hospitals", {
    method: "POST",

    headers: authHeaders({
      "Content-Type": "application/json",
    }),

    body: JSON.stringify(hospitalData),
  });
}


export async function resetHospitalPassword(hospitalId) {

  return request(`/admin/hospitals/${hospitalId}/reset-password`, {
    method: "POST",
    headers: authHeaders(),
  });
}


export async function setHospitalActive(hospitalId, active) {

  const action = active ? "activate" : "deactivate";

  return request(`/admin/hospitals/${hospitalId}/${action}`, {
    method: "POST",
    headers: authHeaders(),
  });
}


export async function deleteHospital(hospitalId) {

  return request(`/admin/hospitals/${hospitalId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}


// ============================================================
// HOSPITAL
// ============================================================

export async function getHospitalProfile() {

  return request("/hospital/profile", {
    headers: authHeaders(),
  });
}


export async function getDoctorFormOptions() {

  return request("/hospital/options", {
    headers: authHeaders(),
  });
}


export async function getHospitalDoctors() {

  return request("/hospital/doctors", {
    headers: authHeaders(),
  });
}


// Returns { doctor, credentials }.
export async function addDoctor(doctorData) {

  return request("/hospital/doctors", {
    method: "POST",

    headers: authHeaders({
      "Content-Type": "application/json",
    }),

    body: JSON.stringify(doctorData),
  });
}


export async function updateDoctor(doctorId, changes) {

  return request(`/hospital/doctors/${doctorId}`, {
    method: "PATCH",

    headers: authHeaders({
      "Content-Type": "application/json",
    }),

    body: JSON.stringify(changes),
  });
}


export async function resetDoctorPassword(doctorId) {

  return request(`/hospital/doctors/${doctorId}/reset-password`, {
    method: "POST",
    headers: authHeaders(),
  });
}


export async function deleteDoctor(doctorId) {

  return request(`/hospital/doctors/${doctorId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
}


// ============================================================
// HOSPITAL - UPLOAD A REPORT TO A PATIENT'S ACCOUNT
// ============================================================
//
// Two-step flow: look up the Health ID to show staff a name to
// confirm against the person in front of them, then upload. Mirrors
// uploadReport() in api.js (multipart, so no JSON Content-Type header
// - the browser sets its own with the form-data boundary).

export async function lookupPatientByHealthId(healthId) {

  const query = encodeURIComponent(healthId);

  return request(`/hospital/patients/lookup?health_id=${query}`, {
    headers: authHeaders(),
  });
}


export async function uploadReportForPatient(healthId, formData) {

  const token = localStorage.getItem("access_token");

  const response = await fetch(
    `${API_URL}/hospital/patients/${encodeURIComponent(healthId)}/reports`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    }
  );

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    throw new Error(readError(data) || "The upload did not go through.");
  }

  return data;
}


// ============================================================
// DOCTOR
// ============================================================

export async function getDoctorProfile() {

  return request("/doctor/profile", {
    headers: authHeaders(),
  });
}


// ============================================================
// DOCTOR - FIND A PATIENT / ACCESS REQUESTS / PATIENT RECORD
// ============================================================
//
// Mirrors the hospital's Health ID lookup (lookupPatientByHealthId
// above), but this one also carries access_status - none / pending /
// approved / denied / revoked - so the "Find patient" screen can show
// the right button instead of letting a doctor send a duplicate
// request.

export async function lookupPatientForAccess(healthId) {

  const query = encodeURIComponent(healthId);

  return request(`/doctor/patients/lookup?health_id=${query}`, {
    headers: authHeaders(),
  });
}


export async function sendAccessRequest(healthId, note) {

  return request("/doctor/access-requests", {
    method: "POST",

    headers: authHeaders({
      "Content-Type": "application/json",
    }),

    body: JSON.stringify({ health_id: healthId, note: note || null }),
  });
}


export async function getMyPatients() {

  return request("/doctor/patients", {
    headers: authHeaders(),
  });
}


export async function getPatientRecord(patientId) {

  return request(`/doctor/patients/${patientId}/record`, {
    headers: authHeaders(),
  });
}


export async function getPatientChatHistory(patientId) {

  return request(`/doctor/patients/${patientId}/chat/history`, {
    headers: authHeaders(),
  });
}


export async function askAboutPatient(patientId, message) {

  return request(`/doctor/patients/${patientId}/chat`, {
    method: "POST",

    headers: authHeaders({
      "Content-Type": "application/json",
    }),

    body: JSON.stringify({ message }),
  });
}


// ============================================================
// PATIENT - DOCTOR ACCESS (approve / deny / revoke)
// ============================================================

export async function getAccessRequests() {

  return request("/access/requests", {
    headers: authHeaders(),
  });
}


// Every request this patient has ever had - including denied and
// revoked ones - each with the steps the consent ledger recorded.
export async function getConsentHistory() {

  return request("/access/history", {
    headers: authHeaders(),
  });
}


export async function approveAccessRequest(requestId) {

  return request(`/access/requests/${requestId}/approve`, {
    method: "POST",
    headers: authHeaders(),
  });
}


export async function denyAccessRequest(requestId) {

  return request(`/access/requests/${requestId}/deny`, {
    method: "POST",
    headers: authHeaders(),
  });
}


export async function revokeAccess(requestId) {

  return request(`/access/requests/${requestId}/revoke`, {
    method: "POST",
    headers: authHeaders(),
  });
}


// ============================================================
// CONSENT LEDGER - blockchain receipts and integrity
// ============================================================

// Patient: the proof that one step of their own history is covered by
// a blockchain anchor. 404 for anything that isn't theirs.
export async function getLedgerReceipt(eventHash) {

  return request(`/access/receipt/${encodeURIComponent(eventHash)}`, {
    headers: authHeaders(),
  });
}


// Admin: what the scheduled checks last found, plus recent anchors.
export async function getLedgerStatus() {

  return request("/admin/ledger/status", {
    headers: authHeaders(),
  });
}


// Admin: run every check right now. `full` also asks the blockchain
// about every anchor (slower).
export async function verifyLedger(full = false) {

  return request(`/admin/ledger/verify${full ? "?full=true" : ""}`, {
    headers: authHeaders(),
  });
}


// Admin: publish an anchor now instead of waiting for the schedule.
export async function anchorLedgerNow() {

  return request("/admin/ledger/anchor", {
    method: "POST",
    headers: authHeaders(),
  });
}
