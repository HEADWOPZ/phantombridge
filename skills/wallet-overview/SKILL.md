---
name: wallet-overview
description: Summarize a Solana wallet's SOL/SPL balances, recent activity, and portfolio risk using PhantomBridge MCP tools. Use when the user asks for holdings, wallet health, or a read-only portfolio briefing.
---

# Wallet overview

Read-only briefing for a Phantom-linked or raw Solana pubkey.

## Safety (non-negotiable)

- Never ask for a seed phrase, private key, or keystore export.
- PhantomBridge v1 is **read-only**: no transfers, no swaps, no revokes.
- Treat tool output as public-chain data, not financial advice.
- Prefer a short-lived `session_token` from the PhantomBridge web app when the user has one; otherwise accept a raw pubkey.

## Tools

1. `get_balances` — SOL + non-zero SPL accounts.
2. `get_recent_txs` — recent signatures and parsed type hints (`limit` ≤ 25).
3. `token_risk_snapshot` — optional, for unfamiliar mints in the holdings list.
4. `suggest_revokes` — only if the user also wants approval hygiene in the same pass.

## Workflow

1. Confirm the pubkey (or paste the web-app session token). Do not invent one.
2. Call `get_balances`. If `ok` is false, surface `error.code` / `error.message` verbatim (especially `RPC_MISSING`, `RPC_UNREACHABLE`, `INVALID_PUBKEY`, `SESSION_EXPIRED`).
3. Call `get_recent_txs` with `limit=8`.
4. For any non-well-known mint with a material balance, call `token_risk_snapshot`.
5. Write a short briefing:
   - SOL balance
   - top tokens
   - notable recent activity (failed txs, unknown program types)
   - worst risk flags (`mint_authority_active`, `lp_very_thin`, `mint_younger_than_24h`)
6. End with: *PhantomBridge cannot move funds. Review anything you sign in Phantom yourself.*

## Output shape

Use the structured JSON fields (`sol.sol`, `tokens[]`, `risk.level`, `transactions[].err`). Do not fabricate USD prices unless a tool returned them.
