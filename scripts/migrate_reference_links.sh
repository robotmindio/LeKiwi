#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != "--apply" ]; }; then
  echo "usage: $0 [--apply]" >&2
  exit 1
fi

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

export CAD_MIGRATION_MODE=${1:+apply}
printf '%s\n' \
  'import runpy, sys' \
  'sys.argv = ["migrate_reference_links.py"]' \
  '_ = runpy.run_path("scripts/migrate_reference_links.py", run_name="__main__")' |
  flatpak run --command=FreeCADCmd --filesystem="$project_dir" org.freecad.FreeCAD -c
