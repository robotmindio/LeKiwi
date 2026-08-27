#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

./scripts/export_robot.sh
python3 scripts/verify_xacro.py URDF/LeKiwi.urdf URDF/LeKiwi.urdf.xacro
./scripts/verify_cad_migration.sh
./scripts/verify_native_part_sources.sh
./scripts/verify_laser_plate_sources.sh
