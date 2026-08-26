#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

printf '%s\n' \
  'import runpy, sys' \
  'sys.argv = ["export_xacro.py", "cad/assembly/LeKiwi.FCStd", "URDF/LeKiwi.urdf.xacro"]' \
  '_ = runpy.run_path("scripts/export_xacro.py", run_name="__main__")' |
  flatpak run --command=FreeCADCmd --filesystem="$project_dir" org.freecad.FreeCAD -c
