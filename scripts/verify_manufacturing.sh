#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

python3 -m scripts.build_reverse_engineered_sources
./scripts/run_freecad_script.sh scripts/verify_reverse_engineered_sources.py
python3 scripts/verify_manufacturing_sources.py
