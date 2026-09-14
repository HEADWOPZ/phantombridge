from phantombridge_mcp.config import WSOL_MINT
from phantombridge_mcp.risk import risk_level, score_token_risk, summarize_portfolio_risk


def test_well_known_is_low() -> None:
    result = score_token_risk(
        mint=WSOL_MINT,
        mint_authority="some",
        freeze_authority="some",
        supply=1,
        decimals=9,
        age_seconds=60,
        age_capped=False,
        liquidity_usd=1.0,
        pair_count=0,
    )
    assert result["level"] == "low"
    assert "well_known_mint" in result["flags"]


def test_young_mintable_thin_lp_is_critical() -> None:
    result = score_token_risk(
        mint="SomeMint1111111111111111111111111111111112",
        mint_authority="Auth1111111111111111111111111111111111111",
        freeze_authority="Auth1111111111111111111111111111111111111",
        supply=1,
        decimals=0,
        age_seconds=3600,
        age_capped=False,
        liquidity_usd=100,
        pair_count=0,
    )
    assert result["score"] >= 80
    assert result["level"] == "critical"
    assert "mint_younger_than_24h" in result["flags"]
    assert "mint_authority_active" in result["flags"]
    assert "lp_very_thin" in result["flags"]


def test_mature_revoked_authorities_deeper_lp_is_low() -> None:
    result = score_token_risk(
        mint="SomeMint1111111111111111111111111111111112",
        mint_authority=None,
        freeze_authority=None,
        supply=1_000_000,
        decimals=6,
        age_seconds=400 * 24 * 3600,
        age_capped=True,
        liquidity_usd=250_000,
        pair_count=3,
    )
    assert result["level"] == "low"
    assert "mint_authority_revoked" in result["flags"]
    assert "lp_deeper" in result["flags"]
    assert "mint_age_lower_bound_only" in result["flags"]


def test_risk_level_bands() -> None:
    assert risk_level(0) == "low"
    assert risk_level(29) == "low"
    assert risk_level(30) == "medium"
    assert risk_level(55) == "high"
    assert risk_level(80) == "critical"
    assert risk_level(200) == "critical"


def test_portfolio_summary() -> None:
    empty = summarize_portfolio_risk([])
    assert empty["score"] == 0
    snaps = [
        {"score": 10, "level": "low"},
        {"score": 90, "level": "critical"},
    ]
    summary = summarize_portfolio_risk(snaps)
    assert summary["high_risk_mints"] == 1
    assert summary["score"] == 90
    assert summary["level"] == "critical"
