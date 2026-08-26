#!/usr/bin/env bash
set -euo pipefail

if ! command -v flatpak >/dev/null; then
    echo "Install Flatpak, then re-run this script." >&2
    exit 1
fi

flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user --noninteractive flathub org.freecad.FreeCAD

flatpak info --user org.freecad.FreeCAD >/dev/null
