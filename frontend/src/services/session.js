// ============================================================
// SESSION
// ============================================================
//
// Four roles now share one login box, so "where does this person go
// after signing in?" and "is this person allowed on this page?" need
// one answer in one place rather than a role check copied into every
// portal.
//
// What is stored here is for ROUTING ONLY - it decides which screen to
// draw. It is not a permission check. Every portal endpoint on the
// backend re-checks the role from the token and refuses accounts that
// still owe a password change, so editing localStorage by hand gets
// you a different-looking empty page and a 403, not access.

const TOKEN_KEY = "access_token";
const ROLE_KEY = "role";
const NAME_KEY = "display_name";
const PENDING_KEY = "must_change_password";

export const HOME_FOR_ROLE = {
  admin: "/admin",
  hospital: "/hospital",
  doctor: "/doctor",
  patient: "/dashboard",
};


export function saveSession(loginResult) {

  localStorage.setItem(TOKEN_KEY, loginResult.access_token);
  localStorage.setItem(ROLE_KEY, loginResult.role || "patient");

  localStorage.setItem(
    PENDING_KEY,
    loginResult.must_change_password ? "true" : "false"
  );

  if (loginResult.display_name) {
    localStorage.setItem(NAME_KEY, loginResult.display_name);
  } else {
    localStorage.removeItem(NAME_KEY);
  }
}


export function clearSession() {

  [TOKEN_KEY, ROLE_KEY, NAME_KEY, PENDING_KEY].forEach((key) =>
    localStorage.removeItem(key)
  );
}


export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}


export function getRole() {
  return localStorage.getItem(ROLE_KEY) || "patient";
}


export function setDisplayName(name) {
  if (name) {
    localStorage.setItem(NAME_KEY, name);
  }
}


export function getDisplayName() {
  return localStorage.getItem(NAME_KEY) || "";
}


export function mustChangePassword() {
  return localStorage.getItem(PENDING_KEY) === "true";
}


export function clearPasswordFlag() {
  localStorage.setItem(PENDING_KEY, "false");
}


/**
 * Where this session belongs right now.
 *
 * An account that has not replaced its issued password goes to the
 * password screen first, whatever its role - that is the whole point
 * of the first-login change.
 */
export function landingPath() {

  if (!getToken()) {
    return "/login";
  }

  if (mustChangePassword()) {
    return "/change-password";
  }

  return HOME_FOR_ROLE[getRole()] || "/dashboard";
}
