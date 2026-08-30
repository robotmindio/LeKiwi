#!/usr/bin/env bash
set -euo pipefail

exec "$(dirname "$0")/run_freecad_script.sh" scripts/import_step_reference.py reference/fusion/LeKiwi.stp cad/assembly/LeKiwi_reference.FCStd
