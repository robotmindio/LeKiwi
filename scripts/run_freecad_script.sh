#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  printf 'usage: %s SCRIPT [ARG...]\n' "$0" >&2
  exit 1
fi

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

cad_script=$1
shift
[[ -f "$cad_script" ]] || { printf 'missing FreeCAD script: %s\n' "$cad_script" >&2; exit 1; }
export CAD_FREECAD_SCRIPT="$cad_script"
export CAD_FREECAD_ARGS_JSON
CAD_FREECAD_ARGS_JSON=$(python3 -c 'import json, sys; print(json.dumps(sys.argv[1:]))' "$@")
printf '%s\n' \
  'import json, os, runpy, sys; sys.path.insert(0, os.getcwd()); _freecad_excepthook = sys.excepthook; sys.excepthook = lambda *args: (_freecad_excepthook(*args), sys.exit(1))' \
  'sys.argv = [os.path.basename(os.environ["CAD_FREECAD_SCRIPT"]), *json.loads(os.environ["CAD_FREECAD_ARGS_JSON"])]' \
  '_ = runpy.run_path(os.environ["CAD_FREECAD_SCRIPT"], run_name="__main__")' |
  flatpak run --command=FreeCADCmd --filesystem="$project_dir" org.freecad.FreeCAD -c
