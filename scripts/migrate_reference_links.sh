#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -gt 1 ] || { [ "$#" -eq 1 ] && [ "$1" != "--apply" ]; }; then
  echo "usage: $0 [--apply]" >&2
  exit 1
fi

export CAD_MIGRATION_MODE=${1:+apply}
exec "$(dirname "$0")/run_freecad_script.sh" scripts/migrate_reference_links.py
