#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

export CAD_COMPARE_ARGS_JSON
CAD_COMPARE_ARGS_JSON=$(python3 -c 'import json, sys; print(json.dumps(sys.argv[1:]))' "$@")
printf '%s\n' \
  'import json, os, runpy, sys' \
  'sys.argv = ["compare_reauthored_assets.py", *json.loads(os.environ["CAD_COMPARE_ARGS_JSON"])]' \
  '_ = runpy.run_path("scripts/compare_reauthored_assets.py", run_name="__main__")' |
  flatpak run --command=FreeCADCmd --filesystem="$project_dir" org.freecad.FreeCAD -c
