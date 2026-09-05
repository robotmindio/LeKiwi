#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

"${CADQUERY_PYTHON:-python3}" scripts/export_so101_wrist.py
./scripts/sync_robotskin_lidar.sh
./scripts/export_cad_meshes.sh
./scripts/export_xacro.sh
