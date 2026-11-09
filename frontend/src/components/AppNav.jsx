import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { clearSession, getDisplayName } from "../services/session";

import BrandMark from "./BrandMark";
import Icon from "./Icon";

/**
 * AppNav
 * ------------------------------------------------------------
 * The patient's navigation. One component, one list - adding a tab
 * means adding a line to LINKS.
 *
 * On a wide screen it is a fixed sidebar; on a phone the same markup
 * becomes a slim top bar with a menu that opens the links as a sheet.
 * The layout switch is all CSS (polish.css) - this file only owns the
 * open/closed state of that sheet.
 *
 * Pass `active` as the key of the current page.
 */

const LINKS = [
  { key: "dashboard", label: "Dashboard", path: "/dashboard", icon: "home" },
  { key: "reports", label: "Reports", path: "/reports", icon: "reports" },
  { key: "doctors", label: "Find a doctor", path: "/doctors", icon: "doctor" },
  { key: "chat", label: "AI Chat", path: "/chat", icon: "chat" },
  { key: "access", label: "Doctor access", path: "/doctor-access", icon: "access" }
];


function initialsOf(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}


function AppNav({ active }) {

  const navigate = useNavigate();

  const [open, setOpen] = useState(false);

  // Dashboard stores the patient's name once it has loaded; on the
  // other tabs it is simply already there.
  const name = getDisplayName();

  // Close the sheet on Escape so it never traps a keyboard user.
  useEffect(() => {

    if (!open) return undefined;

    function onKey(event) {
      if (event.key === "Escape") setOpen(false);
    }

    window.addEventListener("keydown", onKey);

    return () => window.removeEventListener("keydown", onKey);

  }, [open]);

  function go(path) {
    setOpen(false);
    navigate(path);
  }

  function logout() {
    clearSession();
    navigate("/login");
  }

  return (

    <nav
      className={open ? "dashboard-nav app-sidebar is-open" : "dashboard-nav app-sidebar"}
      aria-label="Main"
    >

      <div className="app-sidebar-head">

        <div
          className="dashboard-logo"
          onClick={() => go("/dashboard")}
          role="link"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "Enter") go("/dashboard");
          }}
        >
          <BrandMark onDark />
        </div>

        <button
          type="button"
          className="app-menu-toggle"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-controls="app-sidebar-panel"
          aria-label={open ? "Close menu" : "Open menu"}
        >
          <Icon name={open ? "close" : "menu"} size={22} />
        </button>

      </div>

      <div className="app-sidebar-panel" id="app-sidebar-panel">

        <div className="dashboard-nav-links">

          {LINKS.map((link) => (

            <button
              key={link.key}
              className={
                active === link.key ? "nav-link active" : "nav-link"
              }
              onClick={() => go(link.path)}
              aria-current={active === link.key ? "page" : undefined}
            >
              <Icon name={link.icon} size={19} />
              <span>{link.label}</span>
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
                <small>Patient</small>
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

export default AppNav;
