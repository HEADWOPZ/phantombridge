"""stdio MCP server for Claude Desktop, Cursor, and other MCP clients."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from phantombridge_mcp import tools

mcp = FastMCP(
    "phantombridge",
    instructions=(
        "PhantomBridge is a read-only Solana wallet MCP. "
        "Never ask for seed phrases or private keys. "
        "Never execute swaps, transfers, or revokes. "
        "Return structured JSON from tools and include safety disclaimers."
    ),
)


@mcp.tool()
def get_balances(pubkey: str = "", session_token: str = "") -> dict[str, Any]:
    """Fetch SOL and SPL token balances for a Solana pubkey.

    Accepts a raw base58 pubkey and/or a short-lived pubkey-bound session
    token from the PhantomBridge web app. Never requests private keys.
    """
    return tools.get_balances(pubkey or None, session_token or None)


@mcp.tool()
def get_recent_txs(
    pubkey: str = "",
    session_token: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """List recent transactions for a Solana pubkey (signatures + parsed hints)."""
    return tools.get_recent_txs(pubkey or None, session_token or None, limit)


@mcp.tool()
def token_risk_snapshot(
    mint: str,
    pubkey: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Score a mint using public data: authorities, signature age, DexScreener LP hints.

    Heuristic only — not financial advice and not a guarantee against rugs.
    """
    return tools.token_risk_snapshot(mint, pubkey or None, session_token or None)


@mcp.tool()
def jupiter_quote(
    input_mint: str,
    output_mint: str,
    amount: str,
    slippage_bps: int = 50,
    pubkey: str = "",
    session_token: str = "",
) -> dict[str, Any]:
    """Get a Jupiter swap quote. Does not build, sign, or send a swap."""
    return tools.jupiter_quote(
        input_mint,
        output_mint,
        amount,
        slippage_bps,
        pubkey or None,
        session_token or None,
    )


@mcp.tool()
def suggest_revokes(pubkey: str = "", session_token: str = "") -> dict[str, Any]:
    """Read-only approval / authority hygiene (delegates, close/freeze/mint authorities).

    Drafts revoke suggestions only. Does not send transactions.
    """
    return tools.suggest_revokes(pubkey or None, session_token or None)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
