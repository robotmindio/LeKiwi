#!/usr/bin/env bash
set -euo pipefail

exec "$(dirname "$0")/run_freecad_script.sh" scripts/verify_cad_migration.py URDF/LeKiwi.urdf cad/reference_mapping.json URDF/meshes/reauthored
