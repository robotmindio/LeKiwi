#!/usr/bin/env bash
set -euo pipefail

exec "$(dirname "$0")/run_freecad_script.sh" scripts/export_cad_meshes.py cad/assembly/LeKiwi.FCStd URDF/meshes/reauthored
