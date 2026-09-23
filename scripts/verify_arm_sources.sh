#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
source_dir="$project_dir/cad/upstream/SO-ARM100"
expected_commit=7629d2ad9853d10fb903093a33ef6114099d97e5

if [[ ! -e "$source_dir/.git" ]]; then
  printf 'missing SO-ARM100 source; run: git submodule update --init --recursive\n' >&2
  exit 1
fi

[[ $(git -C "$source_dir" rev-parse HEAD) == "$expected_commit" ]]
for source in \
  LICENSE \
  Simulation/SO101/so101_new_calib.urdf \
  Simulation/SO101/assets/base_motor_holder_so101_v1.stl \
  Simulation/SO101/assets/base_so101_v2.stl \
  Simulation/SO101/assets/motor_holder_so101_base_v1.stl \
  Simulation/SO101/assets/motor_holder_so101_wrist_v1.stl \
  Simulation/SO101/assets/moving_jaw_so101_v1.stl \
  Simulation/SO101/assets/rotation_pitch_so101_v1.stl \
  Simulation/SO101/assets/sts3215_03a_no_horn_v1.stl \
  Simulation/SO101/assets/sts3215_03a_v1.stl \
  Simulation/SO101/assets/under_arm_so101_v1.stl \
  Simulation/SO101/assets/upper_arm_so101_v1.stl \
  Simulation/SO101/assets/waveshare_mounting_plate_so101_v2.stl \
  Simulation/SO101/assets/wrist_roll_follower_so101_v1.stl \
  Simulation/SO101/assets/wrist_roll_pitch_so101_v2.stl; do
  [[ -s "$source_dir/$source" ]]
done

python3 - "$source_dir/Simulation/SO101/so101_new_calib.urdf" <<'PY'
import sys
import xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
expected = {
    "shoulder_pan": ("-1.91986", "1.91986"),
    "shoulder_lift": ("-1.74533", "1.74533"),
    "elbow_flex": ("-1.69", "1.69"),
    "wrist_flex": ("-1.65806", "1.65806"),
    "wrist_roll": ("-2.74385", "2.84121"),
    "gripper": ("-0.174533", "1.74533"),
}
actual = {
    joint.get("name"): (joint.find("limit").get("lower"), joint.find("limit").get("upper"))
    for joint in root.findall("joint") if joint.find("limit") is not None
}
assert actual == expected, actual
PY

printf 'validated SO-101 follower model at %s\n' "$expected_commit"
