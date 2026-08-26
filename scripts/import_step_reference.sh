#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

printf '%s\n' \
  'import runpy, sys' \
  'sys.argv = ["import_step_reference.py", "reference/fusion/LeKiwi.stp", "cad/assembly/LeKiwi_reference.FCStd"]' \
  'runpy.run_path("scripts/import_step_reference.py", run_name="__main__")' |
  flatpak run --command=FreeCADCmd --filesystem="$project_dir" org.freecad.FreeCAD -c
