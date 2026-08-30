#!/usr/bin/env bash
set -euo pipefail

exec "$(dirname "$0")/run_freecad_script.sh" scripts/build_laser_plate_sources.py
