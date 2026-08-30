#!/usr/bin/env bash
set -euo pipefail

exec "$(dirname "$0")/run_freecad_script.sh" scripts/verify_mesh_integrity.py
