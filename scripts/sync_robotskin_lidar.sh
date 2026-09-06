#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

assembly=${1:-cad/assembly/LeKiwi.FCStd}
output_root=${2:-$project_dir}
source_file=cad/upstream/RobotSkin/scad/parts/lekiwi-lidar-base.scad
generated_mesh=$output_root/cad/generated/robotskin-lidar-mount.stl
astra_source=cad/accessories/astra_pro_compact_mount.scad
astra_mesh=$output_root/cad/generated/astra-pro-compact-mount.stl
[[ -f "$source_file" ]] || {
  printf 'missing RobotSkin source; run: git submodule update --init --recursive\n' >&2
  exit 1
}
[[ -f "$astra_source" ]] || {
  printf 'missing Astra compact-mount source: %s\n' "$astra_source" >&2
  exit 1
}
mkdir -p "$(dirname "$generated_mesh")"
if [[ $output_root == "$project_dir" ]]; then
  python3 scripts/sync_sensor_mount_spec.py
else
  python3 scripts/sync_sensor_mount_spec.py --check
fi
openscad -o "$generated_mesh" "$source_file"
openscad -o "$astra_mesh" "$astra_source"

exec "$project_dir/scripts/run_freecad_script.sh" scripts/add_lidar_accessory.py \
  "$assembly" "$source_file" "$generated_mesh" "$astra_source" "$astra_mesh"
