#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "usage: $0 ASSEMBLY.FCStd LINK PART DENSITY_KG_M3 MASS_OVERRIDE_KG" >&2
  exit 1
fi

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

export CAD_ASSEMBLY=$1 CAD_LINK=$2 CAD_PART=$3 CAD_DENSITY=$4 CAD_MASS=$5
printf '%s\n' \
  'import os, runpy, sys' \
  'sys.argv = ["attach_cad_part.py", os.environ["CAD_ASSEMBLY"], os.environ["CAD_LINK"], os.environ["CAD_PART"], os.environ["CAD_DENSITY"], os.environ["CAD_MASS"]]' \
  '_ = runpy.run_path("scripts/attach_cad_part.py", run_name="__main__")' |
  flatpak run --command=FreeCADCmd --filesystem="$project_dir" org.freecad.FreeCAD -c
