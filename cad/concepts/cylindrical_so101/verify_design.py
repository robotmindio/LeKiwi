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
    "shoulder",
    "upper_arm",
    "lower_arm",
    "wrist",
    "gripper",
    "moving_jaw",
    "joint_cover_a",
    "joint_cover_b",
    "clearance_coupon",
    "horn_coupon",
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
                "quality=24",
                "-D",
                "show_motors=false",
                "design.scad",
            )
            if target.stat().st_size < 500:
                raise RuntimeError(f"empty OpenSCAD output: {part}")
            mesh = trimesh.load_mesh(target)
            if not mesh.is_watertight or mesh.body_count != 1 or mesh.volume <= 0:
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
            target = output / f"arm-{pose}.stl"
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
                "quality=24",
                "-D",
                "show_motors=false",
                "design.scad",
            )
            if target.stat().st_size < 500:
                raise RuntimeError(f"empty pose output: {pose}")
            pose_mesh = trimesh.load_mesh(target)
            if not pose_mesh.is_watertight or pose_mesh.volume <= 0:
                raise RuntimeError(f"invalid full-arm solid at {pose} pose")
    print(
        f"verified {len(PARTS)} printable parts, four full-range arm poses, "
        f"{footprint_reduction:.1%} footprint and {material_reduction:.1%} base-material reductions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
