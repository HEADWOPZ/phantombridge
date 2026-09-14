"""Jupiter quote request + parsing (no swap execution)."""

from __future__ import annotations

from typing import Any

from phantombridge_mcp.errors import PhantomBridgeError
from phantombridge_mcp.pubkey import is_valid_pubkey


def validate_quote_args(
    input_mint: str,
    output_mint: str,
    amount: str | int,
    slippage_bps: int,
) -> tuple[str, str, str, int]:
    if not is_valid_pubkey(input_mint):
        raise PhantomBridgeError("INVALID_MINT", "input_mint is not a valid pubkey.")
    if not is_valid_pubkey(output_mint):
        raise PhantomBridgeError("INVALID_MINT", "output_mint is not a valid pubkey.")
    if input_mint.strip() == output_mint.strip():
        raise PhantomBridgeError("INVALID_QUOTE", "input_mint and output_mint must differ.")
    try:
        raw_amount = int(str(amount).strip())
    except ValueError as exc:
        raise PhantomBridgeError(
            "INVALID_AMOUNT",
            "amount must be an integer string of base units (lamports / token atoms).",
        ) from exc
    if raw_amount <= 0:
        raise PhantomBridgeError("INVALID_AMOUNT", "amount must be > 0.")
    if not isinstance(slippage_bps, int) or slippage_bps < 0 or slippage_bps > 10_000:
        raise PhantomBridgeError(
            "INVALID_SLIPPAGE",
            "slippage_bps must be an integer between 0 and 10000.",
        )
    return input_mint.strip(), output_mint.strip(), str(raw_amount), slippage_bps


def parse_jupiter_quote(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PhantomBridgeError("QUOTE_PARSE", "Jupiter quote must be a JSON object.")

    required = ("inputMint", "inAmount", "outputMint", "outAmount")
    missing = [key for key in required if key not in raw or raw[key] in (None, "")]
    if missing:
        raise PhantomBridgeError(
            "QUOTE_PARSE",
            "Jupiter quote is missing required fields.",
            details={"missing": missing},
        )

    try:
        in_amount = int(raw["inAmount"])
        out_amount = int(raw["outAmount"])
    except (TypeError, ValueError) as exc:
        raise PhantomBridgeError("QUOTE_PARSE", "Quote amounts must be integers.") from exc
    if in_amount <= 0 or out_amount <= 0:
        raise PhantomBridgeError("QUOTE_PARSE", "Quote amounts must be positive.")

    impact_raw = raw.get("priceImpactPct")
    try:
        price_impact_pct = float(impact_raw) if impact_raw is not None else None
    except (TypeError, ValueError):
        price_impact_pct = None

    route_plan = raw.get("routePlan") or []
    hops: list[dict[str, Any]] = []
    if isinstance(route_plan, list):
        for hop in route_plan:
            if not isinstance(hop, dict):
                continue
            info = hop.get("swapInfo") if isinstance(hop.get("swapInfo"), dict) else {}
            hops.append(
                {
                    "label": info.get("label") or hop.get("label"),
                    "percent": hop.get("percent"),
                    "input_mint": info.get("inputMint"),
                    "output_mint": info.get("outputMint"),
                    "in_amount": info.get("inAmount"),
                    "out_amount": info.get("outAmount"),
                }
            )

    rate = out_amount / in_amount
    warnings: list[str] = []
    if price_impact_pct is not None and price_impact_pct >= 5:
        warnings.append("high_price_impact_gte_5pct")
    elif price_impact_pct is not None and price_impact_pct >= 1:
        warnings.append("moderate_price_impact_gte_1pct")
    if len(hops) >= 3:
        warnings.append("multi_hop_route")

    other_threshold = raw.get("otherAmountThreshold")
    try:
        min_out = int(other_threshold) if other_threshold is not None else None
    except (TypeError, ValueError):
        min_out = None

    return {
        "input_mint": str(raw["inputMint"]),
        "output_mint": str(raw["outputMint"]),
        "in_amount": str(in_amount),
        "out_amount": str(out_amount),
        "other_amount_threshold": None if min_out is None else str(min_out),
        "swap_mode": raw.get("swapMode") or "ExactIn",
        "slippage_bps": raw.get("slippageBps"),
        "price_impact_pct": price_impact_pct,
        "rate_out_per_in": rate,
        "route": hops,
        "context_slot": raw.get("contextSlot"),
        "swap_usd_value": raw.get("swapUsdValue"),
        "warnings": warnings,
        "execution": "not_supported_v1_read_only",
    }
