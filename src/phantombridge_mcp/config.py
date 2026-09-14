"""Environment configuration. Public endpoints only; paid keys are optional."""

from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_RPC = "https://api.mainnet-beta.solana.com"
DEFAULT_JUPITER = "https://lite-api.jup.ag"
DEFAULT_DEXSCREENER = "https://api.dexscreener.com"

TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
WSOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"

WELL_KNOWN_MINTS = {
    WSOL_MINT: "SOL (wrapped)",
    USDC_MINT: "USDC",
    USDT_MINT: "USDT",
}


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    rpc_url: str | None
    jupiter_api_url: str
    jupiter_api_key: str | None
    dexscreener_api_url: str
    require_rpc: bool
    require_session: bool
    bound_pubkey: str | None
    http_timeout: float

    def resolved_rpc_url(self) -> str:
        if self.require_rpc and not self.rpc_url:
            from phantombridge_mcp.errors import PhantomBridgeError

            raise PhantomBridgeError(
                "RPC_MISSING",
                "SOLANA_RPC_URL is required (PHANTOMBRIDGE_REQUIRE_RPC=1) but was empty.",
                details={"hint": "Set SOLANA_RPC_URL to a Solana JSON-RPC endpoint."},
            )
        if not self.rpc_url:
            from phantombridge_mcp.errors import PhantomBridgeError

            raise PhantomBridgeError(
                "RPC_MISSING",
                "No Solana RPC URL configured.",
                details={
                    "hint": "Set SOLANA_RPC_URL (public default: https://api.mainnet-beta.solana.com)."
                },
            )
        return self.rpc_url


def load_settings() -> Settings:
    raw_rpc = os.environ.get("SOLANA_RPC_URL")
    require_rpc = _flag("PHANTOMBRIDGE_REQUIRE_RPC")
    if raw_rpc is None:
        rpc_url = None if require_rpc else DEFAULT_RPC
    else:
        rpc_url = raw_rpc.strip() or None

    bound = os.environ.get("PHANTOMBRIDGE_BOUND_PUBKEY", "").strip() or None
    timeout_raw = os.environ.get("PHANTOMBRIDGE_HTTP_TIMEOUT", "20").strip()
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = 20.0

    return Settings(
        rpc_url=rpc_url,
        jupiter_api_url=os.environ.get("JUPITER_API_URL", DEFAULT_JUPITER).rstrip("/"),
        jupiter_api_key=os.environ.get("JUPITER_API_KEY", "").strip() or None,
        dexscreener_api_url=os.environ.get(
            "DEXSCREENER_API_URL", DEFAULT_DEXSCREENER
        ).rstrip("/"),
        require_rpc=require_rpc,
        require_session=_flag("PHANTOMBRIDGE_REQUIRE_SESSION"),
        bound_pubkey=bound,
        http_timeout=max(1.0, timeout),
    )
