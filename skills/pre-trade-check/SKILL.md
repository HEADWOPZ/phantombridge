---
name: pre-trade-check
description: Run a read-only pre-trade check on a Solana mint and optional Jupiter quote before the user swaps. Use when the user is about to trade, asks "is this mint safe", or wants a quote without executing.
---

# Pre-trade check

Quote and risk a swap **without executing it**. PhantomBridge v1 never builds, signs, or sends Jupiter swaps.

## Safety (non-negotiable)

- No seed phrases. No private keys. No "just sign this swap" pressure.
- `jupiter_quote` is **quote-only**. If the user asks you to swap, refuse execution and show the quote + warnings instead.
- Heuristics are incomplete. Thin LP + mint authority is a warning, not a proof of fraud or safety.
- Not financial advice.

## Tools

1. `token_risk_snapshot` with the output mint (and input mint if it is not SOL/USDC/USDT).
2. `jupiter_quote` with `input_mint`, `output_mint`, `amount` (base units), `slippage_bps` (default 50).
3. Optional `get_balances` if the user wants to confirm they actually hold the input asset.

## Workflow

1. Collect mints + exact integer `amount` in base units (lamports / token atoms). Do not guess decimals without saying so.
2. Run `token_risk_snapshot` on the asset they are buying.
3. Run `jupiter_quote`.
4. Highlight:
   - `quote.price_impact_pct` and `quote.warnings` (`high_price_impact_gte_5pct`, `multi_hop_route`)
   - `risk.flags` (authorities, age, LP)
   - `quote.out_amount` vs `other_amount_threshold`
5. If `ok` is false (`JUPITER_ERROR`, `RPC_MISSING`, `INVALID_MINT`), stop and report the error.
6. Close with: *v1 will not execute this swap. If you proceed, do it in Phantom / Jupiter yourself after reading the simulation.*

## Known mints (helpers)

- SOL (wrapped): `So11111111111111111111111111111111111111112`
- USDC: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`
- USDT: `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB`
