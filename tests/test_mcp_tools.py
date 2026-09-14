from phantombridge_mcp import tools


def test_five_tool_callables_exist() -> None:
    names = (
        "get_balances",
        "get_recent_txs",
        "token_risk_snapshot",
        "jupiter_quote",
        "suggest_revokes",
    )
    for name in names:
        fn = getattr(tools, name)
        assert callable(fn)
