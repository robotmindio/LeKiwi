#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

source_file=cad/upstream/RobotSkin/scad/parts/lekiwi-lidar-base.scad
generated_mesh=cad/generated/robotskin-lidar-mount.stl
[[ -f "$source_file" ]] || {
  printf 'missing RobotSkin source; run: git submodule update --init --recursive\n' >&2
  exit 1
}
mkdir -p "$(dirname "$generated_mesh")"
openscad -o "$generated_mesh" "$source_file"

exec "$project_dir/scripts/run_freecad_script.sh" scripts/add_lidar_accessory.py cad/assembly/LeKiwi.FCStd cad/upstream/RobotSkin/scad/parts/lekiwi-lidar-base.scad cad/generated/robotskin-lidar-mount.stl
