import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";

import { changePassword } from "../services/portalApi";

import {
  saveSession,
  getToken,
  getRole,
  getDisplayName,
  mustChangePassword,
  landingPath,
  clearSession,
} from "../services/session";

/**
 * ChangePassword
 * ------------------------------------------------------------
 * Two jobs, one screen.
 *
 * On a first login it is compulsory: a hospital or doctor account
 * arrives holding a password that someone else generated and read off
 * a screen, and until it is replaced the API refuses every portal
 * endpoint. So there is no "skip" button here, and no nav bar to
 * escape through - only logout.
 *
 * Reached voluntarily later, it is an ordinary settings screen and the
 * cancel button goes back where you came from.
 */

const MIN_LENGTH = 8;


function ChangePassword() {

  const navigate = useNavigate();

  const forced = mustChangePassword();

  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const [error, setError] = useState("");

  const [busy, setBusy] = useState(false);

  // Declarative, not a navigate() call - navigating during render
  // sets state on another component mid-render and React warns.
  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }

  function handleChange(event) {
    setForm({
      ...form,
      [event.target.name]: event.target.value,
    });
  }

  // Mirrors app/auth/credentials.py::password_problem. Checking here
  // too is only so the person is told before a round trip - the
  // backend is still the one that decides.
  function localProblem() {

    if (form.new_password.length < MIN_LENGTH) {
      return `Use at least ${MIN_LENGTH} characters.`;
    }

    if (!/[a-zA-Z]/.test(form.new_password)) {
      return "Include at least one letter.";
    }

    if (!/[0-9]/.test(form.new_password)) {
      return "Include at least one number.";
    }

    if (form.new_password !== form.confirm_password) {
      return "The two new passwords don't match.";
    }

    if (form.new_password === form.current_password) {
      return "Choose a password you have not used here before.";
    }

    return null;
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const problem = localProblem();

    if (problem) {
      setError(problem);
      return;
    }

    setError("");
    setBusy(true);

    try {

      const result = await changePassword(
        form.current_password,
        form.new_password
      );

      // The response carries a fresh token with the flag cleared, so
      // the session is replaced rather than patched.
      saveSession(result);

      navigate(landingPath(), { replace: true });

    } catch (error) {

      setError(error.message);

    } finally {

      setBusy(false);

    }
  }

  function signOut() {
    clearSession();
    navigate("/login", { replace: true });
  }

  const name = getDisplayName();

  return (

    <div className="portal-page portal-page-narrow">

      <div className="auth-card password-card">

        <h2>
          {forced ? "Set your password" : "Change your password"}
        </h2>

        {forced ? (

          <p className="auth-subtitle">
            {name ? `${name}, you're ` : "You're "}
            signed in with a temporary password that someone else
            generated. Replace it now and the rest of your portal
            opens up.
          </p>

        ) : (

          <p className="auth-subtitle">
            Pick something you haven't used here before.
          </p>

        )}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>

          <div className="form-group">

            <label>
              {forced ? "Temporary password" : "Current password"}
            </label>

            <input
              className="form-input"
              type="password"
              name="current_password"
              value={form.current_password}
              onChange={handleChange}
              autoComplete="current-password"
              required
            />

          </div>


          <div className="form-group">

            <label>New password</label>

            <input
              className="form-input"
              type="password"
              name="new_password"
              value={form.new_password}
              onChange={handleChange}
              autoComplete="new-password"
              required
            />

            <p className="field-hint">
              At least {MIN_LENGTH} characters, with a letter and a
              number.
            </p>

          </div>


          <div className="form-group">

            <label>Confirm new password</label>

            <input
              className="form-input"
              type="password"
              name="confirm_password"
              value={form.confirm_password}
              onChange={handleChange}
              autoComplete="new-password"
              required
            />

          </div>


          <button
            className="primary-btn"
            type="submit"
            disabled={busy}
          >
            {busy ? "Saving…" : "Save password"}
          </button>

        </form>


        <div className="auth-switch">

          {forced ? (

            <>
              Wrong account?

              <button onClick={signOut}>
                Sign out
              </button>
            </>

          ) : (

            <>
              Changed your mind?

              <button
                onClick={() =>
                  navigate(
                    { admin: "/admin", hospital: "/hospital", doctor: "/doctor" }[
                      getRole()
                    ] || "/dashboard"
                  )
                }
              >
                Go back
              </button>
            </>

          )}

        </div>

      </div>

    </div>
  );
}

export default ChangePassword;
