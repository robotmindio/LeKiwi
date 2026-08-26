#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

printf '%s\n' \
  'import runpy, sys' \
  'sys.argv = ["link_base_plate_sources.py"]' \
  '_ = runpy.run_path("scripts/link_base_plate_sources.py", run_name="__main__")' |
  flatpak run --command=FreeCADCmd --filesystem="$project_dir" org.freecad.FreeCAD -c
