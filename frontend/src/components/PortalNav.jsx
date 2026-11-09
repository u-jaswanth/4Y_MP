import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { clearSession, getDisplayName } from "../services/session";

import BrandMark from "./BrandMark";
import Icon from "./Icon";

/**
 * PortalNav
 * ------------------------------------------------------------
 * The sidebar for the staff portals (admin, hospital, doctor).
 * Same shell as the patient's AppNav, so the whole product feels
 * like one app.
 *
 *   role      - "admin" | "hospital" | "doctor"
 *   subtitle  - shown under the name (falls back to the role)
 *   items     - [{ key, label, icon }] the portal's own views
 *   active    - key of the current item
 *   onSelect  - called with an item's key
 *
 * Portals without views (a bare record page) just omit `items`.
 */

const LABEL = {
  admin: "Administrator",
  hospital: "Hospital",
  doctor: "Doctor",
};


function initialsOf(name) {
  return (name || "")
    .replace(/^dr\.?\s+/i, "")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}


function PortalNav({ role, subtitle, items = [], active, onSelect }) {

  const navigate = useNavigate();

  const [open, setOpen] = useState(false);

  const name = getDisplayName() || subtitle || LABEL[role] || "";

  useEffect(() => {

    if (!open) return undefined;

    function onKey(event) {
      if (event.key === "Escape") setOpen(false);
    }

    window.addEventListener("keydown", onKey);

    return () => window.removeEventListener("keydown", onKey);

  }, [open]);

  function pick(key) {
    setOpen(false);
    if (onSelect) onSelect(key);
  }

  function logout() {
    clearSession();
    navigate("/login");
  }

  return (

    <nav
      className={
        open
          ? "dashboard-nav app-sidebar portal-sidebar is-open"
          : "dashboard-nav app-sidebar portal-sidebar"
      }
      aria-label="Portal"
    >

      <div className="app-sidebar-head">

        <div className="dashboard-logo">
          <BrandMark onDark />
        </div>

        <button
          type="button"
          className="app-menu-toggle"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-controls="portal-sidebar-panel"
          aria-label={open ? "Close menu" : "Open menu"}
        >
          <Icon name={open ? "close" : "menu"} size={22} />
        </button>

      </div>

      <div className="app-sidebar-panel" id="portal-sidebar-panel">

        <div className="dashboard-nav-links">

          <span className="portal-role-tag">{LABEL[role] || "Portal"}</span>

          {items.map((item) => (

            <button
              key={item.key}
              className={active === item.key ? "nav-link active" : "nav-link"}
              onClick={() => pick(item.key)}
              aria-current={active === item.key ? "page" : undefined}
            >
              <Icon name={item.icon || "grid"} size={19} />
              <span>{item.label}</span>
            </button>

          ))}

        </div>

        <div className="app-sidebar-foot">

          {name && (
            <div className="app-user">
              <span className="app-user-avatar" aria-hidden="true">
                {initialsOf(name)}
              </span>
              <span className="app-user-text">
                <strong>{name}</strong>
                <small>{subtitle && subtitle !== name ? subtitle : LABEL[role]}</small>
              </span>
            </div>
          )}

          <button className="logout-btn" onClick={logout}>
            <Icon name="logout" size={18} />
            <span>Log out</span>
          </button>

        </div>

      </div>

    </nav>
  );
}

export default PortalNav;
