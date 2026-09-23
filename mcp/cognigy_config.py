"""Shared config storage for the Cognigy Claude plugin.

Credentials are stored per-user (not in the repo) at:
    ~/.claude/cognigy-plugin/config.json

The file only ever contains the API base URL and API key, and is written
with owner-only permissions where the OS supports it.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Optional, TypedDict


class CognigyConfig(TypedDict, total=False):
    api_base_url: str
    api_key: str


def config_dir() -> Path:
    return Path.home() / ".claude" / "cognigy-plugin"


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> CognigyConfig:
    path = config_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    return {
        "api_base_url": data.get("api_base_url", ""),
        "api_key": data.get("api_key", ""),
    }


def save_config(config: CognigyConfig) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = load_config()
    existing.update({k: v for k, v in config.items() if v is not None})

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass  # best-effort on platforms without POSIX permissions (e.g. Windows)

    return path


def is_configured() -> bool:
    cfg = load_config()
    return bool(cfg.get("api_base_url") and cfg.get("api_key"))


def get_base_url() -> Optional[str]:
    return load_config().get("api_base_url") or os.environ.get("COGNIGY_API_BASE_URL")


def get_api_key() -> Optional[str]:
    return load_config().get("api_key") or os.environ.get("COGNIGY_API_KEY")
