#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

printf '%s\n' \
  'import runpy, sys' \
  'sys.argv = ["verify_cad_migration.py", "URDF/LeKiwi.urdf", "cad/reference_mapping.json", "URDF/meshes/reauthored"]' \
  '_ = runpy.run_path("scripts/verify_cad_migration.py", run_name="__main__")' |
  flatpak run --command=FreeCADCmd --filesystem="$project_dir" org.freecad.FreeCAD -c
