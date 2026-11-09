import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import MedicalReports from "./pages/MedicalReports";
import AIChatbot from "./pages/AIChatbot";
import DoctorRecommendation from "./pages/DoctorRecommendation";
import DoctorAccess from "./pages/DoctorAccess";

import ChangePassword from "./pages/ChangePassword";
import AdminDashboard from "./pages/AdminDashboard";
import HospitalDashboard from "./pages/HospitalDashboard";
import DoctorDashboard from "./pages/DoctorDashboard";

import RequireRole from "./components/RequireRole";

import "./App.css";
import "./portal.css";
import "./polish.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>

        {/* ------------------------------------------------
            PUBLIC
        ------------------------------------------------ */}

        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />


        {/* ------------------------------------------------
            PATIENT
        ------------------------------------------------ */}
        {/* Left unguarded, exactly as before - these pages already
            redirect on a failed API call. The guard is applied to the
            staff portals, which are new. */}

        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/reports" element={<MedicalReports />} />
        <Route path="/doctors" element={<DoctorRecommendation />} />
        <Route path="/chat" element={<AIChatbot />} />
        <Route path="/doctor-access" element={<DoctorAccess />} />


        {/* ------------------------------------------------
            ANY SIGNED-IN ROLE
        ------------------------------------------------ */}
        {/* Not wrapped in RequireRole: an account that still owes a
            password change is sent HERE, so guarding it on that
            condition would be a redirect loop. */}

        <Route path="/change-password" element={<ChangePassword />} />


        {/* ------------------------------------------------
            STAFF PORTALS
        ------------------------------------------------ */}

        <Route
          path="/admin"
          element={
            <RequireRole allow="admin">
              <AdminDashboard />
            </RequireRole>
          }
        />

        <Route
          path="/hospital"
          element={
            <RequireRole allow="hospital">
              <HospitalDashboard />
            </RequireRole>
          }
        />

        {/* /doctor is the doctor's own portal. /doctors, above, is the
            patient-facing recommendation page - different audience,
            deliberately one letter apart in the URL because they are
            about the same thing from opposite sides. */}
        <Route
          path="/doctor"
          element={
            <RequireRole allow="doctor">
              <DoctorDashboard />
            </RequireRole>
          }
        />


        <Route path="*" element={<Navigate to="/login" replace />} />

      </Routes>
    </BrowserRouter>
  );
}

export default App;
