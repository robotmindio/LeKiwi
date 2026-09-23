#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

./scripts/verify_reverse_engineered_sources.sh
./scripts/verify_manufacturing_sources.sh
