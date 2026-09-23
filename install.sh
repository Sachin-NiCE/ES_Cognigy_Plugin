#!/usr/bin/env bash
# Installer for the Cognigy Claude plugin (macOS / Linux).
#
# - Finds a usable Python 3.10+ (or installs one via Homebrew / apt / dnf)
# - Creates an isolated virtualenv at ./.venv and installs requirements.txt
# - Points .mcp.json at that venv's interpreter (absolute path)
# - Runs the interactive Cognigy credential setup
#
# Usage:
#   bash install.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MIN_MAJOR=3
MIN_MINOR=10

log() { printf '%s\n' "$*"; }
err() { printf 'Error: %s\n' "$*" >&2; }

version_ok() {
    # $1 = python executable
    "$1" -c "import sys; sys.exit(0 if sys.version_info >= (${MIN_MAJOR}, ${MIN_MINOR}) else 1)" 2>/dev/null
}

find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && version_ok "$candidate"; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

install_python() {
    local os
    os="$(uname -s)"

    if [ "$os" = "Darwin" ]; then
        if command -v brew >/dev/null 2>&1; then
            log "Python ${MIN_MAJOR}.${MIN_MINOR}+ not found. Installing via Homebrew..."
            brew install python@3.12
            return 0
        fi
        err "Python ${MIN_MAJOR}.${MIN_MINOR}+ not found and Homebrew is not installed."
        err "Install Homebrew (https://brew.sh) and re-run, or install Python from https://www.python.org/downloads/"
        return 1
    fi

    # Linux
    if command -v apt-get >/dev/null 2>&1; then
        log "Python ${MIN_MAJOR}.${MIN_MINOR}+ not found. Installing via apt (sudo required)..."
        sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
        return 0
    elif command -v dnf >/dev/null 2>&1; then
        log "Python ${MIN_MAJOR}.${MIN_MINOR}+ not found. Installing via dnf (sudo required)..."
        sudo dnf install -y python3 python3-pip
        return 0
    elif command -v yum >/dev/null 2>&1; then
        log "Python ${MIN_MAJOR}.${MIN_MINOR}+ not found. Installing via yum (sudo required)..."
        sudo yum install -y python3 python3-pip
        return 0
    fi

    err "Python ${MIN_MAJOR}.${MIN_MINOR}+ not found and no supported package manager (apt/dnf/yum) was detected."
    err "Install Python from https://www.python.org/downloads/ and re-run this script."
    return 1
}

PYTHON_BIN="$(find_python || true)"

if [ -z "$PYTHON_BIN" ]; then
    install_python
    PYTHON_BIN="$(find_python || true)"
    if [ -z "$PYTHON_BIN" ]; then
        err "Still could not find a working Python ${MIN_MAJOR}.${MIN_MINOR}+ after installation attempt."
        exit 1
    fi
fi

log "Using Python: $PYTHON_BIN ($("$PYTHON_BIN" --version))"

log "Creating virtual environment at .venv ..."
"$PYTHON_BIN" -m venv "$SCRIPT_DIR/.venv"

VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"

log "Installing dependencies ..."
"$VENV_PYTHON" -m pip install --upgrade pip >/dev/null
"$VENV_PYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt"

log "Wiring .mcp.json to the virtual environment ..."
"$VENV_PYTHON" "$SCRIPT_DIR/scripts/write_mcp_config.py" "$VENV_PYTHON"

log ""
log "Let's connect this plugin to your Cognigy.AI instance."
"$VENV_PYTHON" "$SCRIPT_DIR/scripts/configure.py"

log ""
log "Install complete. In Claude Code, run:"
log "  /plugin marketplace add $SCRIPT_DIR"
log "  /plugin install cognigy@es-cognigy-plugin-dev"
log "then restart Claude Code."
