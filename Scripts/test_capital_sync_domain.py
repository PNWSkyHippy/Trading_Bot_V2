"""Offline regression checks for the broker/DB capital-comparison domain."""

from pathlib import Path
import ast


SOURCE = Path(__file__).resolve().parents[1] / "bot_engine.py"


def load_helper():
    """Load only the pure helper, avoiding BotEngine's startup dependencies."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_paper_brokers_in_capital_breakdown"
    )
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {}
    exec(compile(module, str(SOURCE), "exec"), namespace)
    return namespace[function.name]


def main():
    helper = load_helper()
    assert helper({"brokers": [
        {"broker": "alpaca", "enabled": True, "paper": True},
        {"broker": "kraken", "enabled": True, "paper": True},
        {"broker": "coinbase", "enabled": True, "paper": False},
    ]}) == [
        {"broker": "alpaca", "enabled": True, "paper": True},
        {"broker": "kraken", "enabled": True, "paper": True},
    ]
    assert helper({"brokers": [
        {"broker": "kraken", "enabled": False, "paper": True},
        {"broker": "alpaca", "enabled": True, "paper": False},
    ]}) == []
    assert helper({}) == []
    print("capital-sync comparison-domain tests passed: 3/3")


if __name__ == "__main__":
    main()
