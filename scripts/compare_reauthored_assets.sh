#!/usr/bin/env bash
set -euo pipefail

exec "$(dirname "$0")/run_freecad_script.sh" scripts/compare_reauthored_assets.py "$@"
