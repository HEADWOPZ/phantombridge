"""Heuristic token risk scoring from public mint / LP signals."""

from __future__ import annotations

from typing import Any

from phantombridge_mcp.config import WELL_KNOWN_MINTS, WSOL_MINT

LEVELS = (
    (80, "critical"),
    (55, "high"),
    (30, "medium"),
    (0, "low"),
)


def risk_level(score: int) -> str:
    clamped = max(0, min(100, int(score)))
    for threshold, name in LEVELS:
        if clamped >= threshold:
            return name
    return "low"


def score_token_risk(
    *,
    mint: str,
    mint_authority: str | None,
    freeze_authority: str | None,
    supply: int | None,
    decimals: int | None,
    age_seconds: int | None,
    age_capped: bool,
    liquidity_usd: float | None,
    pair_count: int,
    known_name: str | None = None,
) -> dict[str, Any]:
    """Pure heuristic. Not financial advice; public-data hints only."""
    flags: list[str] = []
    score = 0

    if mint == WSOL_MINT or mint in WELL_KNOWN_MINTS:
        return {
            "mint": mint,
            "score": 2,
            "level": "low",
            "flags": ["well_known_mint"],
            "label": known_name or WELL_KNOWN_MINTS.get(mint),
            "notes": ["Recognized major mint — heuristic risk is informational only."],
        }

    if mint_authority:
        score += 25
        flags.append("mint_authority_active")
    else:
        flags.append("mint_authority_revoked")

    if freeze_authority:
        score += 20
        flags.append("freeze_authority_active")
    else:
        flags.append("freeze_authority_revoked")

    if age_seconds is None:
        score += 10
        flags.append("mint_age_unknown")
    elif age_seconds < 24 * 3600:
        score += 35
        flags.append("mint_younger_than_24h")
    elif age_seconds < 7 * 24 * 3600:
        score += 20
        flags.append("mint_younger_than_7d")
    elif age_seconds < 30 * 24 * 3600:
        score += 8
        flags.append("mint_younger_than_30d")
    else:
        flags.append("mint_age_mature")

    if age_capped:
        flags.append("mint_age_lower_bound_only")

    if liquidity_usd is None:
        score += 12
        flags.append("lp_unknown")
    elif liquidity_usd < 1_000:
        score += 30
        flags.append("lp_very_thin")
    elif liquidity_usd < 10_000:
        score += 18
        flags.append("lp_thin")
    elif liquidity_usd < 50_000:
        score += 8
        flags.append("lp_moderate")
    else:
        flags.append("lp_deeper")

    if pair_count == 0:
        score += 10
        flags.append("no_public_pairs")

    if supply == 0:
        score += 15
        flags.append("zero_supply")
    if decimals is not None and (decimals > 12 or decimals == 0):
        score += 5
        flags.append("unusual_decimals")

    notes = [
        "Heuristics use public mint authorities, signature age, and DexScreener LP hints.",
        "This is not a rug-pull detector and not financial advice.",
    ]
    return {
        "mint": mint,
        "score": max(0, min(100, score)),
        "level": risk_level(score),
        "flags": flags,
        "label": known_name,
        "notes": notes,
    }


def summarize_portfolio_risk(token_snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    if not token_snapshots:
        return {
            "level": "low",
            "score": 0,
            "high_risk_mints": 0,
            "summary": "No SPL holdings to score.",
        }
    scores = [int(item.get("score") or 0) for item in token_snapshots]
    high = sum(1 for item in token_snapshots if item.get("level") in {"high", "critical"})
    worst = max(scores) if scores else 0
    return {
        "level": risk_level(worst),
        "score": worst,
        "average_score": round(sum(scores) / len(scores), 1),
        "high_risk_mints": high,
        "summary": (
            f"{high} holding(s) scored high/critical. Worst score {worst}/100."
            if high
            else f"No high-risk flags. Worst score {worst}/100."
        ),
    }
