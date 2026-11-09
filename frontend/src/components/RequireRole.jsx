import { Navigate } from "react-router-dom";

import {
  getToken,
  getRole,
  mustChangePassword,
  landingPath,
} from "../services/session";

/**
 * RequireRole
 * ------------------------------------------------------------
 * Wraps a portal route. Three redirects, in order:
 *
 *   no token                -> /login
 *   password still to set   -> /change-password
 *   wrong role for this URL -> that role's own home
 *
 * The last one sends people home rather than to an error page: a
 * doctor who bookmarked /hospital has not done anything wrong, they
 * have just typed the wrong address.
 *
 * This is navigation, not security. The API checks the same three
 * things against the token on every request.
 */

function RequireRole({ allow, children }) {

  const roles = Array.isArray(allow) ? allow : [allow];

  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }

  if (mustChangePassword()) {
    return <Navigate to="/change-password" replace />;
  }

  if (!roles.includes(getRole())) {
    return <Navigate to={landingPath()} replace />;
  }

  return children;
}

export default RequireRole;
