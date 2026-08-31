#!/usr/bin/env python3
"""Check generated kinematics and compile the isolated OpenSCAD concept."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import trimesh
from shapely.geometry import Point

from generate_kinematics import LEKIWI, fixed_mounts


HERE = Path(__file__).resolve().parent
PARTS = (
    "base_lower",
    "base_upper",
    "base_column",
    "shoulder",
    "upper_arm",
    "lower_arm",
    "wrist",
    "gripper",
    "moving_jaw",
    "servo_lid",
    "clearance_coupon",
    "horn_coupon",
)
ORIGINAL_MOVING_PARTS = (
    "motor_holder_so101_base_v1.stl",
    "rotation_pitch_so101_v1.stl",
    "upper_arm_so101_v1.stl",
    "under_arm_so101_v1.stl",
    "motor_holder_so101_wrist_v1.stl",
    "wrist_roll_pitch_so101_v2.stl",
    "wrist_roll_follower_so101_v1.stl",
    "moving_jaw_so101_v1.stl",
)


def run(*command: str) -> None:
    completed = subprocess.run(command, cwd=HERE, text=True, capture_output=True)
    if completed.returncode:
        raise RuntimeError(
            f"command failed: {' '.join(command)}\n{completed.stdout}{completed.stderr}"
        )


def area(path: Path) -> float:
    return sum(polygon.area for polygon in trimesh.load_path(path).polygons_full)


def main() -> int:
    if not shutil.which("openscad"):
        raise SystemExit("openscad is required")
    run("python3", "generate_kinematics.py", "--check")
    with tempfile.TemporaryDirectory(prefix="cylindrical-so101-") as temporary:
        output = Path(temporary)
        meshes = {}
        for part in PARTS:
            target = output / f"{part}.stl"
            run(
                "openscad",
                "--hardwarnings",
                "-o",
                str(target),
                "-D",
                f'part="{part}"',
                "-D",
                "quality=16",
                "-D",
                "show_motors=false",
                "-D",
                "show_lids=false",
                "design.scad",
            )
            if target.stat().st_size < 500:
                raise RuntimeError(f"empty OpenSCAD output: {part}")
            mesh = trimesh.load_mesh(target)
            positive_bodies = sum(
                body.volume > 0 for body in mesh.split(only_watertight=False)
            )
            if not mesh.is_watertight or positive_bodies != 1 or mesh.volume <= 0:
                raise RuntimeError(f"invalid printable solid: {part}")
            meshes[part] = mesh

        compact_profiles = {}
        for layer in ("lower", "upper"):
            target = output / f"base-profile-{layer}.dxf"
            run(
                "openscad",
                "--hardwarnings",
                "-o",
                str(target),
                "-D",
                f'part="base_profile_{layer}"',
                "design.scad",
            )
            compact_profiles[layer] = trimesh.load_path(target)
        originals = {
            layer: HERE.parents[2] / f"laser-cut/generated/base_plate_{layer}.dxf"
            for layer in ("lower", "upper")
        }
        footprint_reduction = 1 - area(output / "base-profile-lower.dxf") / area(
            originals["lower"]
        )
        if not 0.10 <= footprint_reduction <= 0.15:
            raise RuntimeError(
                f"unexpected base footprint reduction: {footprint_reduction:.1%}"
            )
        material_reduction = 1 - meshes["base_lower"].volume / (
            area(originals["lower"]) * 7
        )
        if not 0.35 <= material_reduction <= 0.50:
            raise RuntimeError(
                f"unexpected base material reduction: {material_reduction:.1%}"
            )
        new_moving_volume = sum(
            abs(meshes[name].volume)
            for name in (
                "shoulder",
                "upper_arm",
                "lower_arm",
                "wrist",
                "gripper",
                "moving_jaw",
            )
        ) + 5 * abs(meshes["servo_lid"].volume)
        asset_dir = HERE.parents[2] / "cad/upstream/SO-ARM100/Simulation/SO101/assets"
        original_moving_volume = sum(
            abs(trimesh.load_mesh(asset_dir / name).volume) * 1e9
            for name in ORIGINAL_MOVING_PARTS
        )
        arm_material_reduction = 1 - new_moving_volume / original_moving_volume
        if not 0.35 <= arm_material_reduction <= 0.45:
            raise RuntimeError(
                f"unexpected moving-arm material reduction: {arm_material_reduction:.1%}"
            )

        model = ET.parse(LEKIWI).getroot()
        for layer, parent in (
            ("lower", "base_plate_layer1-v5"),
            ("upper", "base_plate_layer2-v3"),
        ):
            outer = max(
                compact_profiles[layer].polygons_full, key=lambda polygon: polygon.area
            ).exterior
            original_profile = trimesh.load_path(originals[layer])
            original_outer = max(
                original_profile.polygons_full, key=lambda polygon: polygon.area
            ).exterior
            for mount in fixed_mounts(model, parent):
                edge_margin = Point(mount).distance(outer)
                original_margin = Point(mount).distance(original_outer)
                required_margin = min(original_margin, 7.8)
                if edge_margin + 0.1 < required_margin:
                    raise RuntimeError(
                        f"{layer} mount {mount} has {edge_margin:.2f} mm edge margin; "
                        f"expected at least {required_margin:.2f} mm"
                    )
        for pose in ("home", "working", "lower_limits", "upper_limits"):
            target = output / f"arm-{pose}.csg"
            run(
                "openscad",
                "--hardwarnings",
                "-o",
                str(target),
                "-D",
                'part="arm"',
                "-D",
                f'pose="{pose}"',
                "-D",
                "quality=16",
                "-D",
                "show_motors=false",
                "-D",
                "show_lids=false",
                "design.scad",
            )
            if target.stat().st_size < 500:
                raise RuntimeError(f"empty pose output: {pose}")
    print(
        f"verified {len(PARTS)} printable parts, four reference arm poses, "
        f"{footprint_reduction:.1%} footprint, {material_reduction:.1%} base-material, "
        f"and {arm_material_reduction:.1%} moving-arm material reductions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
