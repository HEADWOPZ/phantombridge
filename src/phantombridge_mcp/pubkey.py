"""Solana pubkey validation (base58, 32-byte Ed25519)."""

from __future__ import annotations

import re

import base58

from phantombridge_mcp.errors import PhantomBridgeError

_BASE58_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]+$")
PUBKEY_BYTE_LEN = 32


def is_valid_pubkey(value: str | None) -> bool:
    if not value or not isinstance(value, str):
        return False
    trimmed = value.strip()
    if not (32 <= len(trimmed) <= 44):
        return False
    if not _BASE58_RE.fullmatch(trimmed):
        return False
    try:
        raw = base58.b58decode(trimmed)
    except Exception:
        return False
    return len(raw) == PUBKEY_BYTE_LEN


def decode_pubkey(value: str) -> bytes:
    if not is_valid_pubkey(value):
        raise PhantomBridgeError(
            "INVALID_PUBKEY",
            "Value is not a valid Solana public key (base58, 32 bytes).",
            details={"value_preview": (value or "")[:16]},
        )
    return base58.b58decode(value.strip())


def normalize_pubkey(value: str) -> str:
    raw = decode_pubkey(value)
    return base58.b58encode(raw).decode("ascii")
