import { useState } from "react";

/**
 * CredentialsCard
 * ------------------------------------------------------------
 * Shows an issued ID and temporary password once, and says plainly
 * that it is once. The password is generated on the server, hashed
 * immediately, and returned in a single response - nothing can read it
 * back afterwards, so closing this card really does lose it.
 *
 * The copy button copies both lines together, because they are useless
 * apart and copying twice is where people drop one.
 */

function CredentialsCard({ title, credentials, onDone }) {

  const [copied, setCopied] = useState(false);

  if (!credentials) {
    return null;
  }

  const block =
    `ID: ${credentials.login_id}\n` +
    `Temporary password: ${credentials.temporary_password}`;

  async function copyBoth() {

    try {

      await navigator.clipboard.writeText(block);

      setCopied(true);

      setTimeout(() => setCopied(false), 2500);

    } catch {

      // Clipboard access is blocked outside a secure context, which
      // includes plain http on anything other than localhost. The
      // values are on screen either way, so say what happened rather
      // than leaving a button that looks broken.
      setCopied(false);

      window.alert(
        "Your browser blocked the clipboard here. Copy the two values " +
        "off the screen manually."
      );

    }
  }

  return (

    <div className="credentials-card">

      <div className="credentials-head">

        <h3>{title}</h3>

        <p>
          Hand these over now. The password is not stored anywhere in
          readable form, so this is the only time it can be seen.
        </p>

      </div>

      <div className="credentials-values">

        <div className="credential-row">
          <span className="credential-label">ID</span>
          <span className="credential-value">
            {credentials.login_id}
          </span>
        </div>

        <div className="credential-row">
          <span className="credential-label">
            Temporary password
          </span>
          <span className="credential-value">
            {credentials.temporary_password}
          </span>
        </div>

      </div>

      <p className="credentials-note">
        They will be asked to set their own password the first time
        they sign in. Until they do, this account can do nothing else.
      </p>

      <div className="credentials-actions">

        <button className="secondary-btn" onClick={copyBoth}>
          {copied ? "Copied" : "Copy both"}
        </button>

        <button className="primary-btn" onClick={onDone}>
          I've saved these
        </button>

      </div>

    </div>
  );
}

export default CredentialsCard;
