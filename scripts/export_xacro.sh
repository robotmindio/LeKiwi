#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"
temporary=$(mktemp URDF/.LeKiwi.XXXXXX.urdf.xacro)
trap 'rm -f "$temporary"' EXIT

./scripts/run_freecad_script.sh scripts/export_xacro.py cad/assembly/LeKiwi.FCStd "$temporary"
./scripts/run_freecad_script.sh scripts/replace_arm_with_so101.py "$temporary" URDF/LeKiwi.urdf.xacro
