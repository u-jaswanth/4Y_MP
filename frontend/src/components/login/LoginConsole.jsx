import { useState } from "react";
import Icon from "../Icon";
import PortalSelector from "./PortalSelector";
import { PORTALS, PORTAL_FOOTNOTE } from "./portals";

/**
 * LoginConsole
 * ------------------------------------------------------------
 * The right-hand access console: heading, portal selector, the form,
 * and the secondary links. It owns presentation only - every piece of
 * state and the submit handler come from Login.jsx, so the
 * authentication logic stays in one place.
 */

function LoginConsole({
  portal,
  form,
  error,
  busy,
  onSelect,
  onChange,
  onSubmit,
  onRegister,
}) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <section className="mc-console" aria-labelledby="mc-console-title">


      <header className="mc-console-head">
        <h2 id="mc-console-title">Enter MediConnect</h2>
      </header>

      <div className="mc-who">
        <PortalSelector portals={PORTALS} active={portal.key} onSelect={onSelect} />
      </div>

      {/* Re-keyed on the portal so the whole block re-enters when the
          environment switches. */}
      <div className="mc-reveal" key={portal.key}>

        <div className="mc-welcome">
          <h3>{portal.welcome}</h3>
        </div>

        {error && (
          <div className="mc-error" role="alert">
            <Icon name="alert" size={16} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={onSubmit} className="mc-form">

          <div className="mc-field">
            <label htmlFor="login-identifier">{portal.fieldLabel}</label>
            <div className="mc-input">
              <Icon name={portal.fieldIcon} size={18} />
              <input
                id="login-identifier"
                type={portal.inputType}
                name="identifier"
                placeholder={portal.placeholder}
                value={form.identifier}
                onChange={onChange}
                autoComplete="username"
                autoCapitalize="none"
                spellCheck="false"
                required
              />
              <span className="mc-input-line" aria-hidden="true" />
            </div>
          </div>

          <div className="mc-field">
            <label htmlFor="login-password">Password</label>
            <div className="mc-input">
              <Icon name="lock" size={18} />
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                name="password"
                placeholder="Enter your password"
                value={form.password}
                onChange={onChange}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="mc-eye"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                aria-pressed={showPassword}
              >
                <Icon name={showPassword ? "eyeOff" : "eye"} size={18} />
              </button>
              <span className="mc-input-line" aria-hidden="true" />
            </div>
          </div>

          <button
            className={busy ? "mc-enter is-busy" : "mc-enter"}
            type="submit"
            disabled={busy}
          >
            <span className="mc-enter-label">
              {busy ? "Authenticating" : "Enter MediConnect"}
            </span>
            {busy ? (
              <span className="mc-dots" aria-hidden="true"><i /><i /><i /></span>
            ) : (
              <Icon name="arrow" size={18} className="mc-enter-arrow" />
            )}
            <span className="mc-enter-bar" aria-hidden="true" />
          </button>

        </form>

        {portal.key === "patient" ? (
          <div className="mc-secondary">
            <span>New to MediConnect?</span>
            <button type="button" onClick={onRegister}>
              Create account <Icon name="arrow" size={14} />
            </button>
          </div>
        ) : (
          <p className="mc-footnote">{PORTAL_FOOTNOTE[portal.key]}</p>
        )}

      </div>

      <footer className="mc-foot">
        <span className={busy ? "mc-foot-dot is-busy" : "mc-foot-dot"} aria-hidden="true" />
        <span>MediConnect AI © 2026</span>
      </footer>

    </section>
  );
}

export default LoginConsole;
