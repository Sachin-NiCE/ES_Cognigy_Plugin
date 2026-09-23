#!/usr/bin/env python3
"""SessionStart hook: nudge the user to run /cognigy-setup if not configured."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp"))

from cognigy_config import is_configured  # noqa: E402


def main() -> int:
    if is_configured():
        return 0

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "The Cognigy plugin is not yet configured with an API base URL and API key. "
                "If the user wants to use Cognigy features, tell them to run /cognigy-setup."
            ),
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
