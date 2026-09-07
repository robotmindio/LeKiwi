#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/run_freecad_script.sh scripts/build_robotskin_surfaces.py "$@"
for surface in top floor ceiling; do
  openscad -o "cad/generated/robotskin/$surface.stl" \
    -D "surface=\"$surface\"" cad/accessories/robotskin_surfaces.scad
done
python3 scripts/verify_robotskin_surfaces.py
./scripts/run_freecad_script.sh scripts/build_robotskin_surfaces.py --finish
