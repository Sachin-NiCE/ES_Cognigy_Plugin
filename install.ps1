#!/usr/bin/env pwsh
<#
Installer for the Cognigy Claude plugin (Windows).

- Finds a usable Python 3.10+ (or installs one via winget, user-scope, no admin)
- Creates an isolated virtualenv at .\.venv and installs requirements.txt
- Points .mcp.json at that venv's interpreter (absolute path)
- Runs the interactive Cognigy credential setup

Usage:
    powershell -ExecutionPolicy Bypass -File install.ps1
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$MinMajor = 3
$MinMinor = 10

function Test-PythonVersion($exe) {
    try {
        & $exe -c "import sys; sys.exit(0 if sys.version_info >= ($MinMajor, $MinMinor) else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Find-Python {
    foreach ($candidate in @("python", "python3", "py")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd -and (Test-PythonVersion $cmd.Source)) {
            return $cmd.Source
        }
    }
    return $null
}

$PythonBin = Find-Python

if (-not $PythonBin) {
    Write-Host "Python $MinMajor.$MinMinor+ not found."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "Installing Python via winget (current user, no admin needed)..."
        winget install --id Python.Python.3.12 --scope user -e --source winget
    } else {
        Write-Error "winget is not available. Install Python 3.10+ from https://www.python.org/downloads/ (check 'Add python.exe to PATH'), then re-run this script."
        exit 1
    }

    # winget updates PATH for new shells only; refresh for this session.
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    $PythonBin = Find-Python

    if (-not $PythonBin) {
        Write-Error "Python was installed but is not on PATH for this session. Close and reopen your terminal, then re-run install.ps1."
        exit 1
    }
}

Write-Host "Using Python: $PythonBin ($(& $PythonBin --version))"

Write-Host "Creating virtual environment at .venv ..."
& $PythonBin -m venv "$ScriptDir\.venv"

$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"

Write-Host "Installing dependencies ..."
& $VenvPython -m pip install --upgrade pip | Out-Null
& $VenvPython -m pip install -r "$ScriptDir\requirements.txt"

Write-Host "Wiring .mcp.json to the virtual environment ..."
& $VenvPython "$ScriptDir\scripts\write_mcp_config.py" $VenvPython

Write-Host ""
Write-Host "Let's connect this plugin to your Cognigy.AI instance."
& $VenvPython "$ScriptDir\scripts\configure.py"

Write-Host ""
Write-Host "Install complete. In Claude Code, run:"
Write-Host "  /plugin marketplace add $ScriptDir"
Write-Host "  /plugin install cognigy@es-cognigy-plugin-dev"
Write-Host "then restart Claude Code."
