#!/usr/bin/env bash
set -euo pipefail

exec "$(dirname "$0")/run_freecad_script.sh" scripts/seed_robot_metadata.py cad/assembly/LeKiwi_reference.FCStd URDF/LeKiwi.baseline.urdf cad/assembly/LeKiwi.FCStd
