#!/usr/bin/env python3
"""Rewrite .mcp.json to invoke a specific Python interpreter (the plugin's venv)
instead of relying on a bare "python"/"python3" being on PATH.

Usage:
    python write_mcp_config.py /absolute/path/to/venv/python
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: write_mcp_config.py <path-to-python-interpreter>", file=sys.stderr)
        return 1

    python_path = sys.argv[1]
    repo_root = Path(__file__).resolve().parent.parent
    mcp_config_path = repo_root / ".mcp.json"

    config = json.loads(mcp_config_path.read_text(encoding="utf-8"))
    config.setdefault("mcpServers", {}).setdefault("cognigy", {})
    config["mcpServers"]["cognigy"]["command"] = python_path
    config["mcpServers"]["cognigy"]["args"] = ["${CLAUDE_PLUGIN_ROOT}/mcp/server.py"]

    mcp_config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {mcp_config_path} to use interpreter: {python_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
