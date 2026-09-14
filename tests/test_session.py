import time

import base58
from nacl.signing import SigningKey

from phantombridge_mcp.config import Settings
from phantombridge_mcp.errors import PhantomBridgeError
from phantombridge_mcp.session import (
    build_read_proof_message,
    encode_session_token,
    resolve_identity,
    verify_session_token,
)


def _settings(**overrides: object) -> Settings:
    base = dict(
        rpc_url="https://api.mainnet-beta.solana.com",
        jupiter_api_url="https://lite-api.jup.ag",
        jupiter_api_key=None,
        dexscreener_api_url="https://api.dexscreener.com",
        require_rpc=False,
        require_session=False,
        bound_pubkey=None,
        http_timeout=5.0,
    )
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _token(ttl: int = 900, now: int | None = None) -> tuple[str, str, SigningKey]:
    sk = SigningKey.generate()
    pubkey = base58.b58encode(bytes(sk.verify_key)).decode("ascii")
    clock = int(now if now is not None else time.time())
    issued = clock
    expires = clock + ttl
    nonce = "n1"
    message = build_read_proof_message(pubkey, issued_at=issued, expires_at=expires, nonce=nonce)
    sig = sk.sign(message.encode("utf-8")).signature
    payload = {
        "v": 1,
        "pubkey": pubkey,
        "issued_at": issued,
        "expires_at": expires,
        "nonce": nonce,
        "message": message,
        "signature": base58.b58encode(sig).decode("ascii"),
    }
    return encode_session_token(payload), pubkey, sk


def test_verify_valid_session() -> None:
    token, pubkey, _ = _token()
    info = verify_session_token(token)
    assert info["pubkey"] == pubkey
    assert info["verified"] is True


def test_expired_session() -> None:
    now = int(time.time())
    token, _, _ = _token(ttl=10, now=now - 30)
    try:
        verify_session_token(token, now=now)
    except PhantomBridgeError as exc:
        assert exc.code == "SESSION_EXPIRED"
    else:
        raise AssertionError("expected SESSION_EXPIRED")


def test_bad_signature() -> None:
    token, pubkey, _ = _token()
    other = SigningKey.generate()
    # Rebuild with a valid-looking payload but wrong sig
    from phantombridge_mcp.session import decode_session_token

    data = decode_session_token(token)
    data["signature"] = base58.b58encode(bytes(other.sign(b"nope").signature)).decode("ascii")
    bad = encode_session_token(data)
    try:
        verify_session_token(bad)
    except PhantomBridgeError as exc:
        assert exc.code == "INVALID_SESSION"
    else:
        raise AssertionError("expected INVALID_SESSION")
    assert pubkey


def test_resolve_requires_pubkey() -> None:
    try:
        resolve_identity(_settings(), None, None)
    except PhantomBridgeError as exc:
        assert exc.code == "PUBKEY_REQUIRED"
    else:
        raise AssertionError("expected PUBKEY_REQUIRED")


def test_resolve_session_binds_pubkey() -> None:
    token, pubkey, _ = _token()
    ident = resolve_identity(_settings(), None, token)
    assert ident["pubkey"] == pubkey
    assert ident["session_verified"] is True


def test_pubkey_mismatch() -> None:
    token, _, _ = _token()
    other = base58.b58encode(bytes(SigningKey.generate().verify_key)).decode("ascii")
    try:
        resolve_identity(_settings(), other, token)
    except PhantomBridgeError as exc:
        assert exc.code == "PUBKEY_MISMATCH"
    else:
        raise AssertionError("expected PUBKEY_MISMATCH")


def test_require_session_flag() -> None:
    try:
        resolve_identity(_settings(require_session=True), "11111111111111111111111111111111", None)
    except PhantomBridgeError as exc:
        assert exc.code == "SESSION_REQUIRED"
    else:
        raise AssertionError("expected SESSION_REQUIRED")
