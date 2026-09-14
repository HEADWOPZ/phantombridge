import os

from phantombridge_mcp.config import load_settings
from phantombridge_mcp.errors import PhantomBridgeError
from phantombridge_mcp.tools import get_balances, jupiter_quote


def test_require_rpc_missing(monkeypatch) -> None:
    monkeypatch.setenv("PHANTOMBRIDGE_REQUIRE_RPC", "1")
    monkeypatch.setenv("SOLANA_RPC_URL", "")
    settings = load_settings()
    assert settings.rpc_url is None
    try:
        settings.resolved_rpc_url()
    except PhantomBridgeError as exc:
        assert exc.code == "RPC_MISSING"
    else:
        raise AssertionError("expected RPC_MISSING")


def test_get_balances_missing_pubkey() -> None:
    result = get_balances(None, None)
    assert result["ok"] is False
    assert result["error"]["code"] == "PUBKEY_REQUIRED"
    assert result["read_only"] is True


def test_get_balances_invalid_pubkey() -> None:
    result = get_balances("not-a-key", None)
    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_PUBKEY"


def test_jupiter_quote_invalid_amount() -> None:
    result = jupiter_quote(
        "So11111111111111111111111111111111111111112",
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "0",
    )
    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_AMOUNT"


def test_default_rpc_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("SOLANA_RPC_URL", raising=False)
    monkeypatch.delenv("PHANTOMBRIDGE_REQUIRE_RPC", raising=False)
    settings = load_settings()
    assert settings.resolved_rpc_url().startswith("https://")
    # silence unused
    assert os.getenv("PHANTOMBRIDGE_REQUIRE_RPC") in (None, "0", "")
