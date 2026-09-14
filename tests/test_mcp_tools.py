from phantombridge_mcp import tools
from phantombridge_mcp.server import mcp


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


def test_mcp_server_registers_five_tools() -> None:
    manager = mcp._tool_manager
    registered = getattr(manager, "_tools", None) or getattr(manager, "tools", {})
    names = set(registered) if isinstance(registered, dict) else {getattr(t, "name", str(t)) for t in registered}
    assert names == {
        "get_balances",
        "get_recent_txs",
        "token_risk_snapshot",
        "jupiter_quote",
        "suggest_revokes",
    }
