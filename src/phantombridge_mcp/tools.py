"""Read-only MCP tool implementations. No signing, no swaps, no custody."""

from __future__ import annotations

import time
from typing import Any

from phantombridge_mcp.config import (
    TOKEN_2022_PROGRAM,
    TOKEN_PROGRAM,
    WELL_KNOWN_MINTS,
    Settings,
    load_settings,
)
from phantombridge_mcp.errors import PhantomBridgeError, fail_from_exception, ok
from phantombridge_mcp.pubkey import is_valid_pubkey, normalize_pubkey
from phantombridge_mcp.quotes import parse_jupiter_quote, validate_quote_args
from phantombridge_mcp.risk import score_token_risk, summarize_portfolio_risk
from phantombridge_mcp.rpc import HttpClient
from phantombridge_mcp.session import resolve_identity

LAMPORTS_PER_SOL = 1_000_000_000


def _client(settings: Settings | None = None) -> tuple[Settings, HttpClient]:
    cfg = settings or load_settings()
    return cfg, HttpClient(cfg)


def _identity(
    settings: Settings,
    pubkey: str | None,
    session_token: str | None,
) -> dict[str, Any]:
    return resolve_identity(settings, pubkey, session_token)


def _token_accounts(http: HttpClient, owner: str) -> list[dict[str, Any]]:
    accounts: list[dict[str, Any]] = []
    for program_id, program_label in (
        (TOKEN_PROGRAM, "spl-token"),
        (TOKEN_2022_PROGRAM, "token-2022"),
    ):
        result = http.rpc(
            "getParsedTokenAccountsByOwner",
            [owner, {"programId": program_id}, {"encoding": "jsonParsed"}],
        )
        for item in (result or {}).get("value") or []:
            pubkey = item.get("pubkey")
            parsed = (
                ((item.get("account") or {}).get("data") or {}).get("parsed") or {}
            )
            info = parsed.get("info") or {}
            amount_info = info.get("tokenAmount") or {}
            accounts.append(
                {
                    "account": pubkey,
                    "program": program_label,
                    "mint": info.get("mint"),
                    "owner": info.get("owner"),
                    "amount": amount_info.get("amount"),
                    "ui_amount": amount_info.get("uiAmount"),
                    "decimals": amount_info.get("decimals"),
                    "delegate": info.get("delegate"),
                    "delegated_amount": (info.get("delegatedAmount") or {}).get("amount")
                    if isinstance(info.get("delegatedAmount"), dict)
                    else info.get("delegatedAmount"),
                    "state": info.get("state"),
                    "close_authority": info.get("closeAuthority"),
                }
            )
    return accounts


def get_balances(pubkey: str | None = None, session_token: str | None = None) -> dict[str, Any]:
    """SOL + SPL token balances for a pubkey. Read-only."""
    try:
        settings, http = _client()
        try:
            ident = _identity(settings, pubkey, session_token)
            owner = ident["pubkey"]
            lamports = http.rpc("getBalance", [owner])
            if isinstance(lamports, dict):
                lamports = lamports.get("value", 0)
            tokens = _token_accounts(http, owner)
            non_zero = [
                t
                for t in tokens
                if t.get("amount") not in (None, "0", 0)
            ]
            return ok(
                {
                    "pubkey": owner,
                    "session_verified": ident["session_verified"],
                    "sol": {
                        "lamports": int(lamports or 0),
                        "sol": int(lamports or 0) / LAMPORTS_PER_SOL,
                    },
                    "tokens": non_zero,
                    "token_account_count": len(tokens),
                    "non_zero_token_count": len(non_zero),
                }
            )
        finally:
            http.close()
    except Exception as exc:
        return fail_from_exception(exc)


def get_recent_txs(
    pubkey: str | None = None,
    session_token: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Recent signatures and parsed summaries. Read-only."""
    try:
        cap = max(1, min(int(limit), 25))
        settings, http = _client()
        try:
            ident = _identity(settings, pubkey, session_token)
            owner = ident["pubkey"]
            sigs = http.rpc(
                "getSignaturesForAddress",
                [owner, {"limit": cap}],
            ) or []
            transactions: list[dict[str, Any]] = []
            for entry in sigs:
                signature = entry.get("signature")
                parsed = None
                type_hint = "unknown"
                fee = None
                if signature:
                    try:
                        parsed = http.rpc(
                            "getParsedTransaction",
                            [
                                signature,
                                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
                            ],
                        )
                    except PhantomBridgeError:
                        parsed = None
                if parsed:
                    meta = parsed.get("meta") or {}
                    fee = meta.get("fee")
                    err = meta.get("err")
                    instructions = (
                        ((parsed.get("transaction") or {}).get("message") or {}).get(
                            "instructions"
                        )
                        or []
                    )
                    parsed_types = [
                        ix.get("parsed", {}).get("type")
                        for ix in instructions
                        if isinstance(ix, dict) and isinstance(ix.get("parsed"), dict)
                    ]
                    type_hint = next((t for t in parsed_types if t), "unknown")
                else:
                    err = entry.get("err")
                transactions.append(
                    {
                        "signature": signature,
                        "slot": entry.get("slot"),
                        "block_time": entry.get("blockTime"),
                        "err": err,
                        "memo": entry.get("memo"),
                        "fee_lamports": fee,
                        "type_hint": type_hint,
                    }
                )
            return ok(
                {
                    "pubkey": owner,
                    "session_verified": ident["session_verified"],
                    "limit": cap,
                    "transactions": transactions,
                }
            )
        finally:
            http.close()
    except Exception as exc:
        return fail_from_exception(exc)


def _mint_age(http: HttpClient, mint: str) -> tuple[int | None, bool, int | None]:
    sigs = http.rpc("getSignaturesForAddress", [mint, {"limit": 1000}]) or []
    if not sigs:
        return None, False, None
    oldest = sigs[-1]
    block_time = oldest.get("blockTime")
    if not isinstance(block_time, int):
        return None, len(sigs) >= 1000, None
    age = max(0, int(time.time()) - block_time)
    return age, len(sigs) >= 1000, block_time


def _lp_hints(http: HttpClient, mint: str) -> dict[str, Any]:
    url = f"{http.settings.dexscreener_api_url}/latest/dex/tokens/{mint}"
    try:
        data = http.get_json(url, code="LP_LOOKUP_FAILED")
    except PhantomBridgeError as exc:
        return {
            "available": False,
            "error": exc.to_dict()["error"],
            "liquidity_usd": None,
            "pair_count": 0,
            "pairs": [],
        }
    pairs_in = data.get("pairs") if isinstance(data, dict) else None
    pairs: list[dict[str, Any]] = []
    total_lp = 0.0
    if isinstance(pairs_in, list):
        for pair in pairs_in:
            if not isinstance(pair, dict):
                continue
            if pair.get("chainId") not in (None, "solana"):
                continue
            liq = pair.get("liquidity") or {}
            usd = None
            if isinstance(liq, dict) and liq.get("usd") is not None:
                try:
                    usd = float(liq["usd"])
                    total_lp += usd
                except (TypeError, ValueError):
                    usd = None
            created = pair.get("pairCreatedAt")
            pairs.append(
                {
                    "dex": pair.get("dexId"),
                    "pair": pair.get("pairAddress"),
                    "liquidity_usd": usd,
                    "price_usd": pair.get("priceUsd"),
                    "created_at_ms": created,
                    "labels": pair.get("labels"),
                }
            )
    pairs.sort(key=lambda p: (p.get("liquidity_usd") is None, -(p.get("liquidity_usd") or 0)))
    return {
        "available": True,
        "liquidity_usd": total_lp if pairs else None,
        "pair_count": len(pairs),
        "pairs": pairs[:8],
    }


def _mint_meta(http: HttpClient, mint: str) -> dict[str, Any]:
    info = http.rpc("getParsedAccountInfo", [mint, {"encoding": "jsonParsed"}])
    value = (info or {}).get("value")
    if not value:
        raise PhantomBridgeError("MINT_NOT_FOUND", f"No account found for mint {mint}.")
    parsed = ((value.get("data") or {}).get("parsed") or {})
    details = parsed.get("info") or {}
    supply_raw = details.get("supply")
    try:
        supply = int(supply_raw) if supply_raw is not None else None
    except (TypeError, ValueError):
        supply = None
    return {
        "mint_authority": details.get("mintAuthority"),
        "freeze_authority": details.get("freezeAuthority"),
        "supply": supply,
        "decimals": details.get("decimals"),
        "is_initialized": details.get("isInitialized"),
        "owner_program": value.get("owner"),
    }


def token_risk_snapshot(
    mint: str,
    pubkey: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Mint age, authorities, and public LP hints. Read-only heuristics."""
    try:
        mint_n = normalize_pubkey(mint)
        settings, http = _client()
        try:
            ident = None
            if pubkey or session_token or settings.require_session or settings.bound_pubkey:
                ident = _identity(settings, pubkey, session_token)
            meta = _mint_meta(http, mint_n)
            age_seconds, age_capped, first_seen = _mint_age(http, mint_n)
            lp = _lp_hints(http, mint_n)
            snapshot = score_token_risk(
                mint=mint_n,
                mint_authority=meta.get("mint_authority"),
                freeze_authority=meta.get("freeze_authority"),
                supply=meta.get("supply"),
                decimals=meta.get("decimals"),
                age_seconds=age_seconds,
                age_capped=age_capped,
                liquidity_usd=lp.get("liquidity_usd"),
                pair_count=int(lp.get("pair_count") or 0),
                known_name=WELL_KNOWN_MINTS.get(mint_n),
            )
            return ok(
                {
                    "requested_by": None if ident is None else ident["pubkey"],
                    "session_verified": bool(ident and ident["session_verified"]),
                    "mint": mint_n,
                    "mint_meta": meta,
                    "age": {
                        "seconds": age_seconds,
                        "hours": None if age_seconds is None else round(age_seconds / 3600, 2),
                        "first_seen_block_time": first_seen,
                        "lower_bound_only": age_capped,
                    },
                    "lp": lp,
                    "risk": snapshot,
                    "disclaimer": "Heuristic only. Not financial advice. v1 cannot execute trades.",
                }
            )
        finally:
            http.close()
    except Exception as exc:
        return fail_from_exception(exc)


def jupiter_quote(
    input_mint: str,
    output_mint: str,
    amount: str,
    slippage_bps: int = 50,
    pubkey: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Fetch a Jupiter swap quote. Never builds or sends a swap transaction."""
    try:
        inp, out, amt, slip = validate_quote_args(
            input_mint, output_mint, amount, slippage_bps
        )
        settings, http = _client()
        try:
            ident = None
            if pubkey or session_token or settings.require_session or settings.bound_pubkey:
                ident = _identity(settings, pubkey, session_token)
            headers = {"Accept": "application/json"}
            if settings.jupiter_api_key:
                headers["x-api-key"] = settings.jupiter_api_key
            url = f"{settings.jupiter_api_url}/swap/v1/quote"
            raw = http.get_json(
                url,
                params={
                    "inputMint": inp,
                    "outputMint": out,
                    "amount": amt,
                    "slippageBps": str(slip),
                },
                headers=headers,
                code="JUPITER_ERROR",
            )
            parsed = parse_jupiter_quote(raw)
            return ok(
                {
                    "requested_by": None if ident is None else ident["pubkey"],
                    "session_verified": bool(ident and ident["session_verified"]),
                    "quote": parsed,
                    "disclaimer": (
                        "Quote only. PhantomBridge v1 does not assemble, sign, or send swaps."
                    ),
                }
            )
        finally:
            http.close()
    except Exception as exc:
        return fail_from_exception(exc)


def suggest_revokes(
    pubkey: str | None = None,
    session_token: str | None = None,
) -> dict[str, Any]:
    """Read-only approval / authority hygiene. Does not send revoke txs."""
    try:
        settings, http = _client()
        try:
            ident = _identity(settings, pubkey, session_token)
            owner = ident["pubkey"]
            tokens = _token_accounts(http, owner)
            findings: list[dict[str, Any]] = []

            for token in tokens:
                mint = token.get("mint")
                delegated = token.get("delegated_amount")
                try:
                    delegated_i = int(delegated) if delegated not in (None, "") else 0
                except (TypeError, ValueError):
                    delegated_i = 0
                if token.get("delegate") and delegated_i > 0:
                    findings.append(
                        {
                            "kind": "spl_delegate",
                            "severity": "high",
                            "mint": mint,
                            "token_account": token.get("account"),
                            "spender": token.get("delegate"),
                            "delegated_amount": str(delegated_i),
                            "action": (
                                "Draft a Token revoke / approve(0) for this delegate. "
                                "PhantomBridge will not send it."
                            ),
                        }
                    )
                close_auth = token.get("close_authority")
                if close_auth and close_auth != owner:
                    findings.append(
                        {
                            "kind": "close_authority",
                            "severity": "medium",
                            "mint": mint,
                            "token_account": token.get("account"),
                            "authority": close_auth,
                            "action": (
                                "Close authority is not the wallet owner. Review before closing ATA."
                            ),
                        }
                    )
                if token.get("state") == "frozen":
                    findings.append(
                        {
                            "kind": "frozen_account",
                            "severity": "high",
                            "mint": mint,
                            "token_account": token.get("account"),
                            "action": "Account is frozen by mint freeze authority. Do not treat as liquid.",
                        }
                    )

            unique_mints = [m for m in {t.get("mint") for t in tokens if t.get("mint")} if is_valid_pubkey(m)]
            for mint in unique_mints[:20]:
                try:
                    meta = _mint_meta(http, mint)
                except PhantomBridgeError:
                    continue
                if mint in WELL_KNOWN_MINTS:
                    continue
                if meta.get("mint_authority"):
                    findings.append(
                        {
                            "kind": "mint_authority_active",
                            "severity": "medium",
                            "mint": mint,
                            "authority": meta.get("mint_authority"),
                            "action": (
                                "Issuer can still mint. You cannot revoke this unless you are the authority."
                            ),
                        }
                    )
                if meta.get("freeze_authority"):
                    findings.append(
                        {
                            "kind": "freeze_authority_active",
                            "severity": "medium",
                            "mint": mint,
                            "authority": meta.get("freeze_authority"),
                            "action": "Issuer can freeze token accounts. Prefer tokens with freeze revoked.",
                        }
                    )

            high = sum(1 for f in findings if f.get("severity") == "high")
            return ok(
                {
                    "pubkey": owner,
                    "session_verified": ident["session_verified"],
                    "finding_count": len(findings),
                    "high_severity": high,
                    "findings": findings,
                    "draft_only": True,
                    "disclaimer": (
                        "Read-only hygiene report. PhantomBridge v1 never sends revoke or approve txs. "
                        "Review each draft in Phantom before signing anything elsewhere."
                    ),
                }
            )
        finally:
            http.close()
    except Exception as exc:
        return fail_from_exception(exc)
