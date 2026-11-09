const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";


// ============================================================
// NORMAL USER REGISTER
// ============================================================

export async function registerUser(userData) {

  const response = await fetch(
    `${API_URL}/auth/register`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(userData),
    }
  );

  const data = await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Registration failed"
    );

  }

  return data;
}


// ============================================================
// LOGIN
// ============================================================

export async function loginUser(credentials) {

  const response = await fetch(
    `${API_URL}/auth/login`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(credentials),
    }
  );

  const data = await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Login failed"
    );

  }

  return data;
}


// ============================================================
// CURRENT USER
// ============================================================

export async function getCurrentUser() {

  const token =
    localStorage.getItem("access_token");

  const response = await fetch(
    `${API_URL}/auth/me`,
    {
      headers: {
        Authorization:
          `Bearer ${token}`,
      },
    }
  );

  const data =
    await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Failed to get user"
    );

  }

  return data;
}


// ============================================================
// PATIENT REGISTER
// ============================================================

export async function registerPatient(
  patientData
) {

  const formData = new FormData();

  formData.append(
    "full_name",
    patientData.full_name
  );

  formData.append(
    "age",
    patientData.age
  );

  formData.append(
    "gender",
    patientData.gender
  );

  formData.append(
    "mobile",
    patientData.mobile
  );

  formData.append(
    "email",
    patientData.email
  );

  formData.append(
    "password",
    patientData.password
  );

  formData.append(
    "aadhaar_number",
    patientData.aadhaar_number
  );

  formData.append(
    "aadhaar_consent",
    patientData.aadhaar_consent
  );

  formData.append(
    "aadhaar_photo",
    patientData.aadhaar_photo
  );

  const response = await fetch(
    `${API_URL}/auth/register/patient`,
    {
      method: "POST",
      body: formData,
    }
  );

  const data =
    await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Patient registration failed"
    );

  }

  return data;
}


// ============================================================
// PATIENT PROFILE
// ============================================================

export async function getPatientProfile() {

  const token =
    localStorage.getItem("access_token");

  const response = await fetch(
    `${API_URL}/auth/patient/profile`,
    {
      headers: {
        Authorization:
          `Bearer ${token}`,
      },
    }
  );

  const data =
    await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Failed to get patient profile"
    );

  }

  return data;
}


// ============================================================
// UPLOAD REPORT
// ============================================================

export async function uploadReport(
  reportData
) {

  const token =
    localStorage.getItem("access_token");

  const response = await fetch(
    `${API_URL}/reports/upload`,
    {
      method: "POST",

      headers: {
        Authorization:
          `Bearer ${token}`,
      },

      body: reportData,
    }
  );

  const data =
    await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Report upload failed"
    );

  }

  return data;
}


// ============================================================
// GET ALL REPORTS
// ============================================================

export async function getReports() {

  const token =
    localStorage.getItem("access_token");

  const response = await fetch(
    `${API_URL}/reports/`,
    {
      headers: {
        Authorization:
          `Bearer ${token}`,
      },
    }
  );

  const data =
    await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Failed to fetch reports"
    );

  }

  return data;
}


// ============================================================
// GET OVERALL HEALTH SUMMARY
// ============================================================

export async function getHealthSummary() {

  const token =
    localStorage.getItem("access_token");

  const response = await fetch(
    `${API_URL}/reports/summary`,
    {
      headers: {
        Authorization:
          `Bearer ${token}`,
      },
    }
  );

  const data =
    await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Failed to fetch health summary"
    );

  }

  return data;
}


// ============================================================
// RE-SUMMARIZE A REPORT
// ============================================================

// Upload already indexes the report and writes its summary, so this is
// only needed to retry a report that failed, or to regenerate an
// explanation on demand. It replaces the old analyzeReport() call
// against POST /reports/{id}/analyze, which no longer exists.
export async function summarizeReport(reportId) {

  const token =
    localStorage.getItem("access_token");

  const response = await fetch(
    `${API_URL}/reports/${reportId}/summarize`,
    {
      method: "POST",

      headers: {
        Authorization:
          `Bearer ${token}`,
      },
    }
  );

  const data =
    await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Could not summarize this report"
    );

  }

  return data;
}


// ============================================================
// AI CHATBOT
// ============================================================

// `history` is the prior turns of this conversation, oldest first,
// as [{ role: "user" | "assistant", content: "..." }]. Sending it
// lets the backend resolve follow-up questions like "is that high?"
// that only make sense together with what was just discussed.
export async function sendChatMessage(message, history = []) {

  const token =
    localStorage.getItem("access_token");

  const response = await fetch(
    `${API_URL}/chat`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
        Authorization:
          `Bearer ${token}`,
      },

      body: JSON.stringify({ message, history }),
    }
  );

  const data =
    await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Chat request failed"
    );

  }

  return data;
}


// ============================================================
// REPORT FILE / "VIEW" URL
// ============================================================

// The backend returns report.file_url as either:
//  - a full Cloudinary URL (public, no auth needed), or
//  - a relative path like "/reports/{id}/file" served by this API.
// A plain <a target="_blank"> link can't attach an Authorization
// header, so for the relative/local case we append the access
// token as a query param instead.
export function getReportFileUrl(report) {

  if (!report?.file_url) {
    return null;
  }

  if (report.file_url.startsWith("http")) {
    return report.file_url;
  }

  const token =
    localStorage.getItem("access_token");

  const separator =
    report.file_url.includes("?") ? "&" : "?";

  return `${API_URL}${report.file_url}${separator}token=${token}`;
}


// ============================================================
// DOCTOR RECOMMENDATION
// ============================================================

// The dropdown options come from the backend so the choices a user can
// make and the specialties they route to can never drift apart.
export async function getDoctorOptions() {

  const token =
    localStorage.getItem("access_token");

  const response = await fetch(
    `${API_URL}/doctors/options`,
    {
      headers: {
        Authorization:
          `Bearer ${token}`,
      },
    }
  );

  const data =
    await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Could not load the form options"
    );

  }

  return data;
}


export async function recommendDoctors(caseDetails) {

  const token =
    localStorage.getItem("access_token");

  const response = await fetch(
    `${API_URL}/doctors/recommend`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
        Authorization:
          `Bearer ${token}`,
      },

      body: JSON.stringify(caseDetails),
    }
  );

  const data =
    await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Could not find doctors for this case"
    );

  }

  return data;
}


// ============================================================
// LAB VALUE TRENDS (one series per test, across all reports)
// ============================================================

export async function getTrends() {

  const token =
    localStorage.getItem("access_token");

  const response = await fetch(
    `${API_URL}/reports/trends`,
    {
      headers: {
        Authorization:
          `Bearer ${token}`,
      },
    }
  );

  const data =
    await response.json();

  if (!response.ok) {

    throw new Error(
      data.detail ||
      "Could not load your health trends"
    );

  }

  return data;
}
