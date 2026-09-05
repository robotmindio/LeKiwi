"""Record/check the exact source inputs and generated ROS model snapshot."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("URDF/model-manifest.json")


def hashes(root, paths):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def snapshot(root):
    inputs = [root / path for path in (
        "URDF/LeKiwi.urdf",
        "cad/assembly/LeKiwi.FCStd", "cad/accessories/astra_pro_compact_mount.scad",
        "cad/upstream/RobotSkin/scad/parts/lekiwi-lidar-base.scad",
        "cad/upstream/RobotSkin/scad/lib/robotskin.scad",
        "cad/upstream/SO-ARM100/Simulation/SO101/so101_new_calib.urdf",
        "cad/cadquery/so101_part8.py",
        "scripts/export_robot.sh", "scripts/sync_robotskin_lidar.sh",
        "scripts/add_lidar_accessory.py", "scripts/export_cad_meshes.py",
        "scripts/export_xacro.py", "scripts/export_xacro.sh",
        "scripts/export_so101_wrist.py", "scripts/replace_arm_with_so101.py",
        "scripts/cad_utils.py",
    )]
    inputs += list((root / "cad/parts").glob("*.FCStd"))
    inputs += list((root / "cad/upstream/SO-ARM100/Simulation/SO101/assets").glob("*.stl"))
    outputs = [root / "URDF/LeKiwi.urdf.xacro"]
    outputs += list((root / "URDF/meshes/reauthored").glob("*.stl"))
    outputs += list((root / "URDF/meshes/so101").glob("*.stl"))
    return {"inputs": hashes(root, inputs), "outputs": hashes(root, outputs)}


def check(root):
    expected = json.loads((root / MANIFEST).read_text())
    actual = snapshot(root)
    if actual != expected:
        different = [path for group in actual
                     for path in sorted(actual[group].keys() | expected.get(group, {}).keys())
                     if actual[group].get(path) != expected.get(group, {}).get(path)]
        raise ValueError("model needs ./scripts/export_robot.sh: " + ", ".join(different))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        check(ROOT)
        print("generated model matches its source inputs")
    else:
        (ROOT / MANIFEST).write_text(json.dumps(snapshot(ROOT), indent=2) + "\n")
        print(f"recorded {MANIFEST}")
