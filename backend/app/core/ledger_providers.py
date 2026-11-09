"""
Where anchors get published, and how they are checked later.

Every provider has the same two methods:

    publish(digest_hex) -> {"tx_id": str, "state": "pending"|"confirmed", ...}
    check(anchor)       -> {"state": confirmed|pending|mismatch|missing|unreachable,
                            "detail": str, ...}

Providers:
  none   - anchoring switched off. The ledger still works and is still
           checked; it just has no outside witness.
  local  - appends to a file. For trying the flow on a laptop ONLY: the
           file is on the same machine as the database, so it proves
           nothing against someone who controls that machine.
  evm    - a zero-value transaction on an Ethereum-compatible chain
           (Polygon, Ethereum, Base, ...) whose data field carries the
           digest. This is the real one.

No third-party library is needed to READ the chain. Signing a
transaction needs `eth-account` (pip install eth-account), imported
only when the first anchor is published.
"""

import json
import os
import urllib.request
from datetime import datetime

from app.core.ledger_anchor import onchain_payload


class AnchorProviderError(Exception):
    """Publishing failed; the worker records it and retries next tick."""


# ------------------------------------------------------------
# none
# ------------------------------------------------------------

class NullProvider:
    name = "none"
    enabled = False

    def publish(self, digest: str) -> dict:
        raise AnchorProviderError("anchoring is switched off")

    def check(self, anchor: dict) -> dict:
        return {"state": "unreachable", "detail": "anchoring is switched off"}

    def explorer_url(self, tx_id: str):
        return None


# ------------------------------------------------------------
# local (development only)
# ------------------------------------------------------------

class LocalFileProvider:
    name = "local"
    enabled = True

    def __init__(self, path: str):
        self.path = path

    def _read(self) -> list:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def publish(self, digest: str) -> dict:
        tx_id = f"local-{len(self._read()) + 1}"
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "tx_id": tx_id,
                "digest": digest,
                "at": datetime.utcnow().isoformat(),
            }) + "\n")
        return {"tx_id": tx_id, "state": "confirmed", "block_number": None}

    def check(self, anchor: dict) -> dict:
        for row in self._read():
            if row["tx_id"] == anchor["tx_id"]:
                if row["digest"] == anchor["digest"]:
                    return {"state": "confirmed", "detail": "found in local file"}
                return {"state": "mismatch", "detail": "digest differs in local file"}
        return {"state": "missing", "detail": "not in local file"}

    def explorer_url(self, tx_id: str):
        return None


# ------------------------------------------------------------
# evm
# ------------------------------------------------------------

class EvmProvider:
    """Anchors by sending 0 value to ourselves with the digest as data.

    Verifying means: fetch the transaction by hash, then check
      * its data field is exactly CLG1 + digest
      * it was sent FROM the configured anchor address (pinned in
        configuration, never read from the database - otherwise someone
        who rewrites the database could point at their own transaction)
      * it succeeded and has enough confirmations
    """

    name = "evm"
    enabled = True

    def __init__(
        self,
        rpc_url: str,
        chain_id: int,
        address: str,
        private_key: str = None,
        confirmations: int = 12,
        explorer_tx_url: str = None,
        signer=None,
        timeout: int = 20,
    ):
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.address = address.lower() if address else None
        self.private_key = private_key
        self.confirmations = confirmations
        self.explorer_tx_url = explorer_tx_url
        self._signer = signer  # tests inject one; default uses eth-account
        self.timeout = timeout
        self._id = 0

    # --- JSON-RPC -------------------------------------------------
    def _rpc(self, method: str, params: list):
        self._id += 1
        body = json.dumps(
            {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}
        ).encode("utf-8")
        request = urllib.request.Request(
            self.rpc_url, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("error"):
            raise AnchorProviderError(f"{method}: {payload['error']}")
        return payload.get("result")

    @staticmethod
    def _int(value) -> int:
        return int(value, 16) if isinstance(value, str) else int(value)

    # --- signing --------------------------------------------------
    def _sign(self, tx: dict) -> str:
        if self._signer is not None:
            return self._signer(tx)

        try:
            from eth_account import Account  # lazy: only needed to publish
        except ImportError as error:
            raise AnchorProviderError(
                "eth-account is not installed (pip install eth-account)"
            ) from error

        signed = Account.sign_transaction(tx, self.private_key)
        raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
        return "0x" + bytes(raw).hex()

    # --- publish --------------------------------------------------
    def publish(self, digest: str) -> dict:
        if not self.private_key and self._signer is None:
            raise AnchorProviderError("LEDGER_EVM_PRIVATE_KEY is not set")

        data = "0x" + onchain_payload(digest).hex()

        try:
            nonce = self._int(
                self._rpc("eth_getTransactionCount", [self.address, "pending"])
            )
            tip = self._int(self._rpc("eth_maxPriorityFeePerGas", []))
            block = self._rpc("eth_getBlockByNumber", ["latest", False])
            base_fee = self._int(block.get("baseFeePerGas", "0x0"))
            gas = self._int(self._rpc("eth_estimateGas", [{
                "from": self.address, "to": self.address,
                "value": "0x0", "data": data,
            }]))
        except AnchorProviderError:
            raise
        except Exception as error:  # noqa: BLE001
            raise AnchorProviderError(f"could not prepare transaction: {error}") from error

        tx = {
            "chainId": self.chain_id,
            "nonce": nonce,
            "to": self.address,
            "value": 0,
            "data": data,
            "gas": gas + gas // 5,                 # 20% headroom
            "maxPriorityFeePerGas": tip,
            "maxFeePerGas": base_fee * 2 + tip,
            "type": 2,
        }

        try:
            tx_hash = self._rpc("eth_sendRawTransaction", [self._sign(tx)])
        except AnchorProviderError:
            raise
        except Exception as error:  # noqa: BLE001
            raise AnchorProviderError(f"could not send transaction: {error}") from error

        return {"tx_id": tx_hash, "state": "pending", "block_number": None}

    # --- check ----------------------------------------------------
    def check(self, anchor: dict) -> dict:
        expected_data = "0x" + onchain_payload(anchor["digest"]).hex()

        try:
            tx = self._rpc("eth_getTransactionByHash", [anchor["tx_id"]])

            if tx is None:
                return {"state": "missing", "detail": "transaction not found on the node"}

            if (tx.get("input") or "").lower() != expected_data:
                return {"state": "mismatch", "detail": "transaction data is not this digest"}

            if self.address and (tx.get("from") or "").lower() != self.address:
                return {"state": "mismatch", "detail": "sent from an unexpected address"}

            if tx.get("blockNumber") is None:
                return {"state": "pending", "detail": "not in a block yet"}

            receipt = self._rpc("eth_getTransactionReceipt", [anchor["tx_id"]])

            if receipt is None:
                return {"state": "pending", "detail": "no receipt yet"}

            if self._int(receipt.get("status", "0x0")) != 1:
                return {"state": "mismatch", "detail": "transaction reverted"}

            tx_block = self._int(tx["blockNumber"])
            latest = self._int(self._rpc("eth_blockNumber", []))
            depth = latest - tx_block + 1

            if depth < self.confirmations:
                return {
                    "state": "pending",
                    "detail": f"{depth}/{self.confirmations} confirmations",
                    "block_number": tx_block,
                }

            return {
                "state": "confirmed",
                "detail": f"{depth} confirmations",
                "block_number": tx_block,
            }

        except AnchorProviderError as error:
            return {"state": "unreachable", "detail": str(error)}
        except Exception as error:  # noqa: BLE001
            return {"state": "unreachable", "detail": f"{type(error).__name__}: {error}"}

    def explorer_url(self, tx_id: str):
        if self.explorer_tx_url and tx_id:
            return self.explorer_tx_url.rstrip("/") + "/" + tx_id
        return None


# ------------------------------------------------------------
# choosing one from configuration
# ------------------------------------------------------------

def build_provider(cfg: dict):
    """cfg is a plain dict (see app/config.py) so this stays testable."""

    kind = (cfg.get("provider") or "none").lower()

    if kind == "none":
        return NullProvider()

    if kind == "local":
        return LocalFileProvider(cfg.get("local_path") or "ledger_anchors.jsonl")

    if kind == "evm":
        address = cfg.get("evm_address")
        key = cfg.get("evm_private_key")

        if not address and key:
            try:
                from eth_account import Account
                address = Account.from_key(key).address
            except ImportError as error:
                raise AnchorProviderError(
                    "set LEDGER_EVM_ADDRESS, or install eth-account so the "
                    "address can be derived from the key"
                ) from error

        if not cfg.get("evm_rpc_url") or not address or not cfg.get("evm_chain_id"):
            raise AnchorProviderError(
                "LEDGER_EVM_RPC_URL, LEDGER_EVM_CHAIN_ID and an address "
                "(LEDGER_EVM_ADDRESS or LEDGER_EVM_PRIVATE_KEY) are required"
            )

        return EvmProvider(
            rpc_url=cfg["evm_rpc_url"],
            chain_id=int(cfg["evm_chain_id"]),
            address=address,
            private_key=key,
            confirmations=int(cfg.get("evm_confirmations") or 12),
            explorer_tx_url=cfg.get("explorer_tx_url"),
        )

    raise AnchorProviderError(f"unknown LEDGER_ANCHOR_PROVIDER '{kind}'")
