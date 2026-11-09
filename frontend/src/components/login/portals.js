/**
 * Portal definitions for the sign-in screen.
 *
 * The first block of fields (key, label, fieldLabel, placeholder, hint,
 * inputType) is the original TABS config from Login.jsx, unchanged.
 * Everything below it is presentation copy for the redesigned screen.
 */

export const PORTALS = [
  {
    key: "patient",
    label: "Patient",
    fieldLabel: "Email",
    placeholder: "you@example.com",
    hint: "Sign in with the email you registered with.",
    inputType: "email",
    fieldIcon: "mail",
    icon: "patient",
    tagline: "Your health space",
    welcome: "Welcome back, Patient.",
    intro: "Access your health records and medical intelligence.",
    stageNote: "Reports explained in plain language, with access in your hands.",
    accessCard: { value: "Patient controlled", note: "You choose who sees what" },
  },
  {
    key: "doctor",
    label: "Doctor",
    fieldLabel: "Doctor ID",
    placeholder: "DOC-P4X9R2",
    hint: "The ID your hospital issued you.",
    inputType: "text",
    fieldIcon: "badge",
    icon: "doctor",
    tagline: "Clinical workspace",
    welcome: "Welcome back, Doctor.",
    intro: "Open your clinical workspace.",
    stageNote: "Records from patients who have approved your access.",
    accessCard: { value: "Shared by approval", note: "Patients grant access" },
  },
  {
    key: "hospital",
    label: "Hospital",
    fieldLabel: "Hospital ID",
    placeholder: "HOSP-K7M2Q4",
    hint: "The ID your administrator issued you.",
    inputType: "text",
    fieldIcon: "badge",
    icon: "hospital",
    tagline: "Care infrastructure",
    welcome: "Welcome back, Hospital.",
    intro: "Manage your hospital and its doctors.",
    stageNote: "Your hospital, your doctors, one place to run them.",
    accessCard: { value: "Doctors you manage", note: "Issued by your hospital" },
  },
  {
    key: "admin",
    label: "Admin",
    fieldLabel: "Admin email or ID",
    placeholder: "admin@mediconnect.ai",
    hint: "The administrator account for this platform.",
    inputType: "text",
    fieldIcon: "mail",
    icon: "admin",
    tagline: "Platform control",
    welcome: "Welcome back, Admin.",
    intro: "Oversee hospitals and the platform.",
    stageNote: "Hospitals and platform oversight.",
    accessCard: { value: "Platform oversight", note: "Hospitals are added here" },
  },
];

export const PORTAL_BY_KEY = Object.fromEntries(PORTALS.map((p) => [p.key, p]));

export const PORTAL_LABEL = {
  patient: "the patient dashboard",
  hospital: "the hospital portal",
  doctor: "the doctor portal",
  admin: "the admin portal",
};

export const PORTAL_FOOTNOTE = {
  hospital: "Hospitals are added by the platform administrator, not by signing up here.",
  doctor: "Doctors are added by their hospital, not by signing up here.",
  admin: "There is a single administrator account for this platform.",
};
