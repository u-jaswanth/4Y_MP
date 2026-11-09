// ============================================================
// LEDGER PROOF (runs in the browser)
// ============================================================
//
// Re-does, on the patient's own device, the two calculations that tie a
// receipt to a blockchain anchor - so the page does not just take the
// server's word that "proof_valid" is true.
//
//   1. event hash + Merkle proof  ->  must give the batch's Merkle root
//   2. SHA-256("consent-ledger-anchor-v1|from|to|head|root")
//                                 ->  must give the anchor's digest
//
// What this cannot do is read the blockchain. The last step - that the
// transaction really carries this digest - is done by the patient
// opening the transaction on a block explorer (the panel shows exactly
// what to compare).
//
// These mirror app/core/ledger_merkle.py and app/core/ledger_anchor.py
// byte for byte; if one changes, the other must.

const ANCHOR_VERSION = "consent-ledger-anchor-v1";

// "CLG1" - the 4 bytes in front of the digest inside the transaction.
export const ONCHAIN_PREFIX_HEX = "434c4731";


function hexToBytes(hex) {

  if (typeof hex !== "string" || hex.length % 2 !== 0 || /[^0-9a-f]/i.test(hex)) {
    throw new Error("Malformed hash in receipt.");
  }

  const bytes = new Uint8Array(hex.length / 2);

  for (let i = 0; i < bytes.length; i += 1) {
    bytes[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }

  return bytes;
}


function bytesToHex(bytes) {

  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}


function concat(...parts) {

  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));

  let offset = 0;

  for (const part of parts) {
    out.set(part, offset);
    offset += part.length;
  }

  return out;
}


async function sha256(bytes) {

  // crypto.subtle only exists on https:// pages and on localhost.
  if (!globalThis.crypto?.subtle) {
    throw new Error(
      "This browser can't run the check here (it needs a secure https page)."
    );
  }

  return new Uint8Array(await globalThis.crypto.subtle.digest("SHA-256", bytes));
}


/**
 * @param receipt the object returned by GET /access/receipt/{hash}
 * @returns {{merkleOk: boolean, digestOk: boolean}}
 */
export async function verifyReceipt(receipt) {

  let running = await sha256(
    concat(Uint8Array.of(0), hexToBytes(receipt.event_hash))
  );

  for (const step of receipt.proof || []) {

    const sibling = hexToBytes(step.hash);

    if (step.side === "left") {
      running = await sha256(concat(Uint8Array.of(1), sibling, running));
    } else if (step.side === "right") {
      running = await sha256(concat(Uint8Array.of(1), running, sibling));
    } else {
      return { merkleOk: false, digestOk: false };
    }
  }

  const merkleOk = bytesToHex(running) === receipt.merkle_root;

  const text =
    `${ANCHOR_VERSION}|${receipt.from_seq}|${receipt.to_seq}|` +
    `${receipt.head_hash}|${receipt.merkle_root}`;

  const digest = bytesToHex(await sha256(new TextEncoder().encode(text)));

  return { merkleOk, digestOk: digest === receipt.digest };
}


// What the transaction's "input data" field must contain.
export function expectedOnchainData(receipt) {

  return `0x${ONCHAIN_PREFIX_HEX}${receipt.digest}`;
}
