#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

build_dir=$(mktemp -d "$project_dir/.verify-robot.XXXXXX")
cleanup() {
  python3 - "$build_dir" <<'PY'
import shutil
import sys
shutil.rmtree(sys.argv[1])
PY
}
trap cleanup EXIT

./scripts/verify_arm_sources.sh
"${CADQUERY_PYTHON:-python3}" cad/cadquery/test_so101_wrist.py
./scripts/export_robot.sh --output-root "$build_dir"
./scripts/run_freecad_script.sh scripts/verify_arm_mount.py \
  "$build_dir/cad/assembly/LeKiwi.FCStd" "$build_dir/URDF/LeKiwi.urdf.xacro"
./scripts/run_freecad_script.sh scripts/verify_sensor_mounts.py \
  "$build_dir/cad/assembly/LeKiwi.FCStd" "$build_dir/URDF/LeKiwi.urdf.xacro"
python3 scripts/verify_xacro.py URDF/LeKiwi.urdf "$build_dir/URDF/LeKiwi.urdf.xacro"
./scripts/run_freecad_script.sh scripts/verify_cad_migration.py \
  URDF/LeKiwi.urdf cad/reference_mapping.json "$build_dir/URDF/meshes/reauthored"
./scripts/verify_native_part_sources.sh
./scripts/verify_laser_plate_sources.sh
./scripts/verify_accessory_sources.sh
./scripts/verify_mesh_integrity.sh
