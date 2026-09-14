from phantombridge_mcp.errors import PhantomBridgeError
from phantombridge_mcp.pubkey import is_valid_pubkey, normalize_pubkey

# Well-known valid Solana addresses
WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SYSTEM = "11111111111111111111111111111111"


def test_valid_known_mints() -> None:
    assert is_valid_pubkey(WSOL)
    assert is_valid_pubkey(USDC)
    assert is_valid_pubkey(SYSTEM)


def test_normalize_roundtrip() -> None:
    assert normalize_pubkey(f"  {USDC}  ") == USDC


def test_rejects_empty_and_garbage() -> None:
    assert not is_valid_pubkey("")
    assert not is_valid_pubkey(None)  # type: ignore[arg-type]
    assert not is_valid_pubkey("not-a-key")
    assert not is_valid_pubkey("0xabc")
    assert not is_valid_pubkey("O0O0O0O0O0O0O0O0O0O0O0O0O0O0O0O0")  # invalid base58 chars


def test_rejects_wrong_length() -> None:
    assert not is_valid_pubkey("2")
    assert not is_valid_pubkey("1" * 64)


def test_normalize_invalid_raises() -> None:
    try:
        normalize_pubkey("nope")
    except PhantomBridgeError as exc:
        assert exc.code == "INVALID_PUBKEY"
    else:
        raise AssertionError("expected INVALID_PUBKEY")
