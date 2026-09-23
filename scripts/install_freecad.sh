#!/usr/bin/env bash
set -euo pipefail

if ! command -v flatpak >/dev/null; then
    echo "Install Flatpak, then re-run this script." >&2
    exit 1
fi

freecad_commit=893800da1d18ef978377b002d47780513f3a5d810e09f7494bc79f0e7122c1ff

flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
# Older Flatpak (Ubuntu 24.04) only accepts --commit on update, so pin in two steps.
flatpak install --user --noninteractive flathub org.freecad.FreeCAD//stable
flatpak update --user --noninteractive --commit="$freecad_commit" org.freecad.FreeCAD//stable

test "$(flatpak info --user --show-commit org.freecad.FreeCAD)" = "$freecad_commit"
