import { useState } from "react";

import { getLedgerReceipt } from "../services/portalApi";
import { verifyReceipt, expectedOnchainData } from "../services/ledgerProof";
import { formatDateTime } from "../services/dates";

/**
 * ReceiptVerifier
 * ------------------------------------------------------------
 * The "Verify" control on one step of the patient's consent history.
 *
 * Fetches the step's proof from the server, then re-does the maths in
 * the browser (see services/ledgerProof.js). The one thing it cannot do
 * itself is look inside the blockchain, so it shows the patient the
 * exact value to compare on the block explorer.
 *
 * `provider` "local" is a development mode that writes to a file on the
 * server - it is labelled as such rather than passed off as a
 * blockchain.
 */

function ReceiptVerifier({ eventHash }) {

  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [receipt, setReceipt] = useState(null);
  const [checks, setChecks] = useState(null);
  const [copied, setCopied] = useState(false);


  async function toggle() {

    if (open) {
      setOpen(false);
      return;
    }

    setOpen(true);

    // Always re-fetch: a step that was "waiting" a minute ago may have
    // been anchored since.
    setLoading(true);
    setError("");

    try {

      const data = await getLedgerReceipt(eventHash);

      setReceipt(data);

      setChecks(data.anchored ? await verifyReceipt(data) : null);

    } catch (loadError) {

      setError(loadError.message || "Could not load this receipt.");

    } finally {

      setLoading(false);

    }
  }


  async function copyExpected() {

    try {
      await navigator.clipboard.writeText(expectedOnchainData(receipt));
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }


  const isTestMode = receipt?.provider === "local";
  const allGood = checks?.merkleOk && checks?.digestOk;


  return (

    <div className="verify-wrap">

      <button
        type="button"
        className="link-btn history-verify"
        aria-expanded={open}
        onClick={toggle}
      >
        {open ? "Hide check" : "Verify this receipt"}
      </button>

      {open && (

        <div className="verify-panel">

          {loading && <p className="portal-note">Checking…</p>}

          {error && <div className="error-message">{error}</div>}

          {!loading && receipt && !receipt.anchored && (
            <p className="portal-note">{receipt.detail}</p>
          )}

          {!loading && receipt?.anchored && checks && (

            <>

              <ul className="verify-checks">

                <li className={checks.merkleOk ? "verify-ok" : "verify-bad"}>
                  {checks.merkleOk
                    ? `This step is inside a published batch (log entries ${receipt.from_seq}–${receipt.to_seq}).`
                    : "This step does NOT match the published batch."}
                </li>

                <li className={checks.digestOk ? "verify-ok" : "verify-bad"}>
                  {checks.digestOk
                    ? "The batch fingerprint was recalculated on your device and matches."
                    : "The batch fingerprint does NOT match."}
                </li>

                <li
                  className={
                    receipt.status === "confirmed" && !isTestMode
                      ? "verify-ok"
                      : "verify-wait"
                  }
                >
                  {isTestMode
                    ? "Test mode: the fingerprint is saved on the server's own disk, not on a blockchain."
                    : receipt.status === "confirmed"
                      ? "The blockchain transaction is confirmed."
                      : "The blockchain transaction is waiting for confirmations - check again in a few minutes."}
                </li>

              </ul>

              {!allGood && (
                <div className="error-message">
                  This receipt does not check out. Keep the receipt code
                  and contact the platform administrator.
                </div>
              )}

              {!isTestMode && allGood && (

                <div className="verify-onchain">

                  <p className="portal-note">
                    To see it for yourself, open the transaction and
                    compare its <strong>input data</strong> with the
                    value below.
                  </p>

                  <code className="verify-code">
                    {expectedOnchainData(receipt)}
                  </code>

                  <div className="verify-actions">

                    <button
                      type="button"
                      className="link-btn"
                      onClick={copyExpected}
                    >
                      {copied ? "Copied" : "Copy value"}
                    </button>

                    {receipt.explorer_url && (
                      <a
                        className="link-btn"
                        href={receipt.explorer_url}
                        target="_blank"
                        rel="noreferrer noopener"
                      >
                        Open transaction ↗
                      </a>
                    )}

                  </div>

                </div>

              )}

              {receipt.tx_id && (
                <span className="entity-sub verify-tx">
                  Transaction {receipt.tx_id}
                </span>
              )}

              <span className="entity-sub">
                Step recorded {formatDateTime(receipt.created_at)}
              </span>

            </>

          )}

        </div>

      )}

    </div>
  );
}

export default ReceiptVerifier;
