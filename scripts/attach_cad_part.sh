#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "usage: $0 ASSEMBLY.FCStd LINK PART DENSITY_KG_M3 MASS_OVERRIDE_KG" >&2
  exit 1
fi

exec "$(dirname "$0")/run_freecad_script.sh" scripts/attach_cad_part.py "$@"
