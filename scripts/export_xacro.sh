#!/usr/bin/env bash
set -euo pipefail

exec "$(dirname "$0")/run_freecad_script.sh" scripts/export_xacro.py cad/assembly/LeKiwi.FCStd URDF/LeKiwi.urdf.xacro
