"""Pubkey-bound, short-lived read-proof sessions. Never stores private keys."""

from __future__ import annotations

import base64
import json
import time
from typing import Any

import base58
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from phantombridge_mcp.config import Settings
from phantombridge_mcp.errors import PhantomBridgeError
from phantombridge_mcp.pubkey import decode_pubkey, normalize_pubkey

SESSION_PREFIX = "PhantomBridge read-proof"


def encode_session_token(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_session_token(token: str) -> dict[str, Any]:
    padded = token.strip() + "=" * (-len(token.strip()) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise PhantomBridgeError(
            "INVALID_SESSION",
            "Session token is not valid base64url JSON.",
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(data, dict):
        raise PhantomBridgeError("INVALID_SESSION", "Session token JSON must be an object.")
    return data


def build_read_proof_message(
    pubkey: str,
    *,
    issued_at: int,
    expires_at: int,
    nonce: str,
) -> str:
    return "\n".join(
        [
            SESSION_PREFIX,
            "v=1",
            f"pubkey={pubkey}",
            f"issued_at={issued_at}",
            f"expires_at={expires_at}",
            f"nonce={nonce}",
        ]
    )


def verify_ed25519(pubkey: str, message: str, signature_b58: str) -> None:
    key_bytes = decode_pubkey(pubkey)
    try:
        sig = base58.b58decode(signature_b58)
    except Exception as exc:
        raise PhantomBridgeError(
            "INVALID_SESSION",
            "Session signature is not valid base58.",
        ) from exc
    if len(sig) != 64:
        raise PhantomBridgeError(
            "INVALID_SESSION",
            "Session signature must be 64 bytes.",
        )
    try:
        VerifyKey(key_bytes).verify(message.encode("utf-8"), sig)
    except BadSignatureError as exc:
        raise PhantomBridgeError(
            "INVALID_SESSION",
            "Read-proof signature does not match pubkey.",
        ) from exc


def verify_session_token(token: str, *, now: int | None = None) -> dict[str, Any]:
    data = decode_session_token(token)
    pubkey = data.get("pubkey")
    message = data.get("message")
    signature = data.get("signature")
    expires_at = data.get("expires_at")
    issued_at = data.get("issued_at")
    nonce = data.get("nonce")

    if not isinstance(pubkey, str) or not isinstance(message, str):
        raise PhantomBridgeError("INVALID_SESSION", "Session missing pubkey or message.")
    if not isinstance(signature, str):
        raise PhantomBridgeError("INVALID_SESSION", "Session missing signature.")
    if not isinstance(expires_at, int) or not isinstance(issued_at, int):
        raise PhantomBridgeError("INVALID_SESSION", "Session timestamps must be integers.")
    if not isinstance(nonce, str) or not nonce:
        raise PhantomBridgeError("INVALID_SESSION", "Session missing nonce.")

    pubkey = normalize_pubkey(pubkey)
    clock = int(time.time() if now is None else now)
    if expires_at <= issued_at:
        raise PhantomBridgeError("INVALID_SESSION", "Session expiry is not after issued_at.")
    if clock >= expires_at:
        raise PhantomBridgeError(
            "SESSION_EXPIRED",
            "Read-proof session has expired. Re-sign in the web app.",
            details={"expires_at": expires_at, "now": clock},
        )
    if clock + 3600 < issued_at:
        raise PhantomBridgeError("INVALID_SESSION", "Session issued_at is too far in the future.")

    expected = build_read_proof_message(
        pubkey, issued_at=issued_at, expires_at=expires_at, nonce=nonce
    )
    if message.strip() != expected:
        raise PhantomBridgeError(
            "INVALID_SESSION",
            "Session message does not match the canonical read-proof format.",
        )
    if not message.startswith(SESSION_PREFIX):
        raise PhantomBridgeError("INVALID_SESSION", "Session message is not a PhantomBridge proof.")

    verify_ed25519(pubkey, message, signature)
    return {
        "pubkey": pubkey,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": nonce,
        "verified": True,
    }


def resolve_identity(
    settings: Settings,
    pubkey: str | None,
    session_token: str | None,
) -> dict[str, Any]:
    session_info: dict[str, Any] | None = None
    session_pubkey: str | None = None

    if session_token and session_token.strip():
        session_info = verify_session_token(session_token)
        session_pubkey = session_info["pubkey"]
    elif settings.require_session:
        raise PhantomBridgeError(
            "SESSION_REQUIRED",
            "PHANTOMBRIDGE_REQUIRE_SESSION=1 — pass a short-lived session_token from the web app.",
        )

    raw_pubkey = (pubkey or "").strip() or session_pubkey
    if not raw_pubkey:
        raise PhantomBridgeError(
            "PUBKEY_REQUIRED",
            "Provide a Solana pubkey or a pubkey-bound session_token.",
        )

    normalized = normalize_pubkey(raw_pubkey)
    if session_pubkey and session_pubkey != normalized:
        raise PhantomBridgeError(
            "PUBKEY_MISMATCH",
            "Requested pubkey does not match the session-bound wallet.",
            details={"requested": normalized, "session": session_pubkey},
        )
    if settings.bound_pubkey:
        bound = normalize_pubkey(settings.bound_pubkey)
        if bound != normalized:
            raise PhantomBridgeError(
                "PUBKEY_MISMATCH",
                "Requested pubkey does not match PHANTOMBRIDGE_BOUND_PUBKEY.",
                details={"requested": normalized, "bound": bound},
            )

    return {
        "pubkey": normalized,
        "session": session_info,
        "session_verified": bool(session_info),
    }
