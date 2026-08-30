#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

python3 scripts/build_reverse_engineered_sources.py
exec "$project_dir/scripts/run_freecad_script.sh" scripts/verify_reverse_engineered_sources.py
