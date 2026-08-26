#!/usr/bin/env bash
set -euo pipefail

if ! command -v apt-get >/dev/null; then
    echo "This installer requires a Debian/Ubuntu system with apt-get." >&2
    exit 1
fi

if (( EUID == 0 )); then
    apt-get update
    apt-get install --yes freecad
elif command -v sudo >/dev/null; then
    sudo apt-get update
    sudo apt-get install --yes freecad
else
    echo "Run this script as root, or install sudo." >&2
    exit 1
fi

command -v FreeCAD >/dev/null || command -v freecad >/dev/null
