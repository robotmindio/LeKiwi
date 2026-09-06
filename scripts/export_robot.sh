#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_dir"

output_root=$project_dir
if [[ ${1:-} == --output-root && -n ${2:-} && $# == 2 ]]; then
  output_root=$(realpath -m "$2")
elif (( $# )); then
  echo "usage: $0 [--output-root DIRECTORY]" >&2
  exit 1
fi

assembly=$output_root/cad/assembly/LeKiwi.FCStd
if [[ $output_root != "$project_dir" ]]; then
  mkdir -p "$(dirname "$assembly")" "$output_root/URDF/meshes/reauthored"
  cp --reflink=auto cad/assembly/LeKiwi.FCStd "$assembly"
  ln -s "$project_dir/cad/parts" "$output_root/cad/parts"
fi

generated_root=$output_root/cad/generated
"${CADQUERY_PYTHON:-python3}" scripts/export_so101_wrist.py \
  "$generated_root/so101/native_wrist_flex.stl"
./scripts/sync_robotskin_lidar.sh "$assembly" "$output_root"
./scripts/run_freecad_script.sh scripts/export_cad_meshes.py \
  "$assembly" "$output_root/URDF/meshes/reauthored"
LEKIWI_GENERATED_ROOT=$generated_root ./scripts/run_freecad_script.sh \
  scripts/export_xacro.py "$assembly" "$output_root/URDF/.LeKiwi.generated.urdf.xacro"
LEKIWI_GENERATED_ROOT=$generated_root ./scripts/run_freecad_script.sh \
  scripts/replace_arm_with_so101.py "$output_root/URDF/.LeKiwi.generated.urdf.xacro" \
  "$output_root/URDF/LeKiwi.urdf.xacro"
rm "$output_root/URDF/.LeKiwi.generated.urdf.xacro"
if [[ $output_root == "$project_dir" ]]; then
  python3 scripts/model_manifest.py
fi
