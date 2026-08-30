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
  STEP/SO100/Base_08q.step \
  STEP/SO100/Motor1_holder.step \
  STEP/SO100/Passive_Horn_01.step \
  STEP/SO100/Rotation_Pitch_08i.step \
  STEP/SO100/SO_ARM100_08k.step \
  STEP/SO100/STS3215_03a.step \
  STEP/SO100/Wrist_Roll_Pitch_08i.step \
  'STEP/SO100/Follower_Specific/Moving_Jaw_08d v1.step' \
  'STEP/SO100/Follower_Specific/SO_5DOF_ARM100_Assembly.step' \
  'STEP/SO100/Follower_Specific/Wrist_Roll_08c v1.step'; do
  [[ -s "$source_dir/$source" ]]
done

printf 'validated SO-ARM100 follower STEP source at %s\n' "$expected_commit"
