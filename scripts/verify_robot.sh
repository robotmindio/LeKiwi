#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

./scripts/verify_arm_sources.sh
"${CADQUERY_PYTHON:-python3}" cad/cadquery/test_so101_wrist.py
./scripts/export_robot.sh
./scripts/run_freecad_script.sh scripts/verify_arm_mount.py
python3 scripts/verify_xacro.py URDF/LeKiwi.urdf URDF/LeKiwi.urdf.xacro
./scripts/verify_cad_migration.sh
./scripts/verify_native_part_sources.sh
./scripts/verify_laser_plate_sources.sh
./scripts/verify_accessory_sources.sh
./scripts/verify_reverse_engineered_sources.sh
./scripts/verify_mesh_integrity.sh
./scripts/verify_manufacturing_sources.sh
