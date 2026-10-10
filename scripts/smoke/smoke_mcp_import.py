"""Smoke test for official MCP Python SDK imports."""

import mcp


def run_smoke():
    print(f"MCP SDK smoke test passed: package {mcp.__file__}")


if __name__ == "__main__":
    run_smoke()
