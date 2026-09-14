---
name: approval-audit
description: Draft Solana token-approval and authority hygiene (delegates, close/freeze/mint authorities) using PhantomBridge suggest_revokes. Use when the user asks to revoke approvals, check spenders, or audit token account permissions.
---

# Approval audit

Read-only hygiene report. **Draft** revoke advice only — never send `revoke`, `approve`, or `setAuthority` transactions.

## Safety (non-negotiable)

- Never request keys or seed phrases.
- Never claim you revoked something. You only listed findings.
- A mint/freeze authority on a token the user *holds* is usually **not** theirs to revoke.
- Infinite or leftover SPL delegates (`spl_delegate`) are the usual user-actionable items.
- Frozen accounts are not liquid; do not treat them as spendable.

## Tools

1. `suggest_revokes` — primary.
2. `get_balances` — context for which accounts still have balances.
3. `token_risk_snapshot` — optional, for each high-severity mint.

## Workflow

1. Take pubkey or `session_token`.
2. Call `suggest_revokes`.
3. Group findings by `kind`:
   - `spl_delegate` — user-actionable; name spender + delegated amount.
   - `close_authority` — review before closing ATAs.
   - `frozen_account` — do not trade.
   - `mint_authority_active` / `freeze_authority_active` — issuer risk; usually not user-revocable.
4. For each `spl_delegate`, draft (do not execute) a human instruction:
   - Token account, mint, spender, amount
   - "In Phantom or a trusted revoke UI, revoke this delegate. PhantomBridge will not send the tx."
5. If `error.code` is `RPC_MISSING` / `RPC_UNREACHABLE`, say so clearly.

## Output

A table of findings + a one-line reminder: *Read-only. No custody. Review every signature in Phantom.*
