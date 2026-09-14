import pytest

from phantombridge_mcp.errors import PhantomBridgeError
from phantombridge_mcp.quotes import parse_jupiter_quote, validate_quote_args

WSOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


def test_validate_quote_args_ok() -> None:
    inp, out, amt, slip = validate_quote_args(WSOL, USDC, "100000000", 50)
    assert inp == WSOL
    assert amt == "100000000"
    assert slip == 50


def test_validate_rejects_same_mint() -> None:
    with pytest.raises(PhantomBridgeError) as exc:
        validate_quote_args(WSOL, WSOL, "1", 50)
    assert exc.value.code == "INVALID_QUOTE"


def test_validate_rejects_bad_amount() -> None:
    with pytest.raises(PhantomBridgeError) as exc:
        validate_quote_args(WSOL, USDC, "nope", 50)
    assert exc.value.code == "INVALID_AMOUNT"
    with pytest.raises(PhantomBridgeError) as exc2:
        validate_quote_args(WSOL, USDC, "0", 50)
    assert exc2.value.code == "INVALID_AMOUNT"


def test_validate_rejects_slippage() -> None:
    with pytest.raises(PhantomBridgeError) as exc:
        validate_quote_args(WSOL, USDC, "1", 10_001)
    assert exc.value.code == "INVALID_SLIPPAGE"


def test_parse_jupiter_quote() -> None:
    raw = {
        "inputMint": WSOL,
        "inAmount": "100000000",
        "outputMint": USDC,
        "outAmount": "10186375",
        "otherAmountThreshold": "10135444",
        "swapMode": "ExactIn",
        "slippageBps": 50,
        "priceImpactPct": "0.00007",
        "routePlan": [
            {
                "percent": 100,
                "swapInfo": {
                    "label": "HumidiFi",
                    "inputMint": WSOL,
                    "outputMint": USDC,
                    "inAmount": "100000000",
                    "outAmount": "10186375",
                },
            }
        ],
        "contextSlot": 1,
        "swapUsdValue": "10.18",
    }
    parsed = parse_jupiter_quote(raw)
    assert parsed["out_amount"] == "10186375"
    assert parsed["rate_out_per_in"] == pytest.approx(0.10186375)
    assert parsed["warnings"] == []
    assert parsed["route"][0]["label"] == "HumidiFi"
    assert parsed["execution"] == "not_supported_v1_read_only"


def test_parse_flags_high_impact_and_hops() -> None:
    raw = {
        "inputMint": WSOL,
        "inAmount": "100",
        "outputMint": USDC,
        "outAmount": "1",
        "priceImpactPct": "6.5",
        "routePlan": [
            {"swapInfo": {"label": "A"}},
            {"swapInfo": {"label": "B"}},
            {"swapInfo": {"label": "C"}},
        ],
    }
    parsed = parse_jupiter_quote(raw)
    assert "high_price_impact_gte_5pct" in parsed["warnings"]
    assert "multi_hop_route" in parsed["warnings"]


def test_parse_missing_fields() -> None:
    with pytest.raises(PhantomBridgeError) as exc:
        parse_jupiter_quote({"inputMint": WSOL})
    assert exc.value.code == "QUOTE_PARSE"
