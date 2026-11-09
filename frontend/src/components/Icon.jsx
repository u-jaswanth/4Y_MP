/**
 * Icon
 * ------------------------------------------------------------
 * A small set of line icons drawn inline, so the app needs no icon
 * package. All share one 24px grid and a 1.75 stroke so they sit
 * together as a family. Decorative by default (aria-hidden); pass
 * `label` when an icon stands alone without text beside it.
 */

const PATHS = {
  home: (
    <>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 9.5V20h14V9.5" />
      <path d="M10 20v-6h4v6" />
    </>
  ),
  reports: (
    <>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5" />
      <path d="M9 13h6M9 17h4" />
    </>
  ),
  doctor: (
    <>
      <path d="M6 3v6a4 4 0 0 0 8 0V3" />
      <path d="M10 13v2a5 5 0 0 0 10 0v-1" />
      <circle cx="20" cy="12" r="2" />
    </>
  ),
  chat: (
    <>
      <path d="M21 12a8 8 0 0 1-11.7 7.1L4 20.5l1.4-4.6A8 8 0 1 1 21 12z" />
      <path d="M9 11h6M9 14h3" />
    </>
  ),
  access: (
    <>
      <path d="M12 3 5 6v5.5c0 4.3 2.9 7.8 7 9.5 4.1-1.7 7-5.2 7-9.5V6z" />
      <path d="m9 12 2.2 2.2L15.5 10" />
    </>
  ),
  logout: (
    <>
      <path d="M9 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h3" />
      <path d="M16 8l4 4-4 4M20 12H9" />
    </>
  ),
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  close: <path d="M6 6l12 12M18 6 6 18" />,
  upload: (
    <>
      <path d="M12 16V4M7 9l5-5 5 5" />
      <path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
    </>
  ),
  spark: (
    <>
      <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" />
      <path d="M19 16v4M17 18h4" />
    </>
  ),
  check: <path d="m5 12.5 4.5 4.5L19 7.5" />,
  pulse: <path d="M3 12h4l2.5-6 4 12 2.5-6H21" />,
  file: (
    <>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5" />
    </>
  ),
  hospital: (
    <>
      <path d="M4 21V6a1 1 0 0 1 1-1h9a1 1 0 0 1 1 1v15" />
      <path d="M15 11h4a1 1 0 0 1 1 1v9M2 21h20" />
      <path d="M9.5 8v5M7 10.5h5" />
    </>
  ),
  users: (
    <>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3 20a6 6 0 0 1 12 0" />
      <path d="M16 5a3.2 3.2 0 0 1 0 6M18 20a6 6 0 0 0-3-5.2" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="3.6" />
      <path d="M4.5 20a7.5 7.5 0 0 1 15 0" />
    </>
  ),
  chain: (
    <>
      <path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" />
      <path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />
    </>
  ),
  grid: (
    <>
      <rect x="4" y="4" width="7" height="7" rx="1.5" />
      <rect x="13" y="4" width="7" height="7" rx="1.5" />
      <rect x="4" y="13" width="7" height="7" rx="1.5" />
      <rect x="13" y="13" width="7" height="7" rx="1.5" />
    </>
  ),
  plus: <path d="M12 5v14M5 12h14" />,
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.5 4.5" />
    </>
  ),
  alert: (
    <>
      <path d="M12 4 2.8 19.5h18.4z" />
      <path d="M12 10v4.5M12 17.2v.1" />
    </>
  ),
  patient: (
    <>
      <path d="M12 20.5s-7.5-4.4-7.5-10A4.3 4.3 0 0 1 12 7.8a4.3 4.3 0 0 1 7.5 2.7c0 5.6-7.5 10-7.5 10z" />
      <path d="M7.5 12.5h2.2l1.3-2.4 2 4.2 1.2-1.8h2.3" />
    </>
  ),
  admin: (
    <>
      <path d="M4 7h10M18 7h2M4 12h4M12 12h8M4 17h12M20 17h0" />
      <circle cx="16" cy="7" r="2" />
      <circle cx="10" cy="12" r="2" />
      <circle cx="18" cy="17" r="2" />
    </>
  ),
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  eye: (
    <>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
      <circle cx="12" cy="12" r="2.8" />
    </>
  ),
  eyeOff: (
    <>
      <path d="M4 4l16 16" />
      <path d="M9.9 5.8A9.6 9.6 0 0 1 12 5.5c6 0 9.5 6.5 9.5 6.5a16 16 0 0 1-3.2 4M6.3 7.6A15.7 15.7 0 0 0 2.5 12S6 18.5 12 18.5c1.4 0 2.7-.3 3.8-.8" />
      <path d="M10 10a2.8 2.8 0 0 0 4 4" />
    </>
  ),
  mail: (
    <>
      <rect x="3" y="5.5" width="18" height="13" rx="2.2" />
      <path d="m4 7.5 8 6 8-6" />
    </>
  ),
  badge: (
    <>
      <rect x="3.5" y="5" width="17" height="14" rx="2.2" />
      <circle cx="9" cy="11" r="2" />
      <path d="M5.8 16c.6-1.7 1.9-2.5 3.2-2.5s2.6.8 3.2 2.5M14.5 10h3.5M14.5 13.5H18" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </>
  ),
};


function Icon({ name, size = 20, label, className = "" }) {

  const body = PATHS[name];

  if (!body) return null;

  return (
    <svg
      className={`icon ${className}`.trim()}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
    >
      {body}
    </svg>
  );
}

export default Icon;
