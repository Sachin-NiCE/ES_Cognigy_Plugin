#!/usr/bin/env python3
"""Interactive setup/update for the Cognigy Claude plugin.

Run standalone:
    python scripts/configure.py

Or non-interactively:
    python scripts/configure.py --base-url https://api-trial.cognigy.ai --api-key XXXX

Re-running this at any time updates the stored credentials.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp"))

from cognigy_config import load_config, save_config, config_path  # noqa: E402


def prompt_value(label: str, current: str, secret: bool = False) -> str:
    suffix = " [unchanged]" if current else ""
    reader = getpass.getpass if secret else input
    display_current = ("*" * 6) if (secret and current) else current
    value = reader(f"{label} (current: {display_current or 'not set'}){suffix}: ").strip()
    return value or current


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure the Cognigy Claude plugin.")
    parser.add_argument("--base-url", help="Cognigy API base URL, e.g. https://api-trial.cognigy.ai")
    parser.add_argument("--api-key", help="Cognigy API key")
    parser.add_argument("--show", action="store_true", help="Show current config (key masked) and exit")
    args = parser.parse_args()

    current = load_config()

    if args.show:
        base = current.get("api_base_url") or "not set"
        key = "set" if current.get("api_key") else "not set"
        print(f"Config file: {config_path()}")
        print(f"  api_base_url: {base}")
        print(f"  api_key: {key}")
        return 0

    base_url = args.base_url
    api_key = args.api_key

    if not base_url and not api_key:
        print("Cognigy Claude Plugin setup")
        print("---------------------------")
        base_url = prompt_value("Cognigy API base URL", current.get("api_base_url", ""))
        api_key = prompt_value("Cognigy API key", current.get("api_key", ""), secret=True)
    else:
        base_url = base_url or current.get("api_base_url", "")
        api_key = api_key or current.get("api_key", "")

    if not base_url or not api_key:
        print("Both an API base URL and an API key are required.", file=sys.stderr)
        return 1

    base_url = base_url.rstrip("/")

    path = save_config({"api_base_url": base_url, "api_key": api_key})
    print(f"Saved Cognigy configuration to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
