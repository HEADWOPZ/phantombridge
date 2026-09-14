"""Local smoke-test CLI (same JSON the MCP tools return)."""

from __future__ import annotations

import argparse
import json
import sys

from phantombridge_mcp import tools


def _print(result: dict) -> int:
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m phantombridge_mcp.cli",
        description="Invoke PhantomBridge tools without an MCP client.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_bal = sub.add_parser("get_balances")
    p_bal.add_argument("pubkey", nargs="?", default="")
    p_bal.add_argument("--session", default="")

    p_tx = sub.add_parser("get_recent_txs")
    p_tx.add_argument("pubkey", nargs="?", default="")
    p_tx.add_argument("--session", default="")
    p_tx.add_argument("--limit", type=int, default=5)

    p_risk = sub.add_parser("token_risk_snapshot")
    p_risk.add_argument("mint")
    p_risk.add_argument("--pubkey", default="")
    p_risk.add_argument("--session", default="")

    p_q = sub.add_parser("jupiter_quote")
    p_q.add_argument("input_mint")
    p_q.add_argument("output_mint")
    p_q.add_argument("amount")
    p_q.add_argument("--slippage-bps", type=int, default=50)
    p_q.add_argument("--pubkey", default="")
    p_q.add_argument("--session", default="")

    p_rev = sub.add_parser("suggest_revokes")
    p_rev.add_argument("pubkey", nargs="?", default="")
    p_rev.add_argument("--session", default="")

    args = parser.parse_args(argv)

    if args.cmd == "get_balances":
        return _print(tools.get_balances(args.pubkey or None, args.session or None))
    if args.cmd == "get_recent_txs":
        return _print(tools.get_recent_txs(args.pubkey or None, args.session or None, args.limit))
    if args.cmd == "token_risk_snapshot":
        return _print(tools.token_risk_snapshot(args.mint, args.pubkey or None, args.session or None))
    if args.cmd == "jupiter_quote":
        return _print(
            tools.jupiter_quote(
                args.input_mint,
                args.output_mint,
                args.amount,
                args.slippage_bps,
                args.pubkey or None,
                args.session or None,
            )
        )
    if args.cmd == "suggest_revokes":
        return _print(tools.suggest_revokes(args.pubkey or None, args.session or None))
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
