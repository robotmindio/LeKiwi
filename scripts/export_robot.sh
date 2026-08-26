#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

./scripts/export_cad_meshes.sh
./scripts/export_xacro.sh
