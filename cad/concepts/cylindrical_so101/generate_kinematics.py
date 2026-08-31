#!/usr/bin/env python3
"""Generate OpenSCAD constants from the canonical SO-101/LeKiwi Xacro."""

from __future__ import annotations

import argparse
import math
import xml.etree.ElementTree as ET
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SO101 = ROOT / "cad/upstream/SO-ARM100/Simulation/SO101/so101_new_calib.urdf"
LEKIWI = ROOT / "URDF/LeKiwi.urdf.xacro"
OUTPUT = HERE / "generated/kinematics.scad"
JOINTS = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)
LINKS = (
    "base_link",
    "shoulder_link",
    "upper_arm_link",
    "lower_arm_link",
    "wrist_link",
    "gripper_link",
)
SERVO_SHAFT = [12.5, 0.0, 18.7]
ARM_PLATE_HOLES = ([20.0, 60.0], [40.0, 60.0], [20.0, 80.0], [40.0, 80.0])


def vector(element: ET.Element, attribute: str, scale: float = 1.0) -> list[float]:
    values = [float(value) * scale for value in element.get(attribute).split()]
    if len(values) != 3 or not all(math.isfinite(value) for value in values):
        raise ValueError(f"invalid {attribute}: {element.get(attribute)!r}")
    return values


def number(value: float) -> str:
    value = 0.0 if abs(value) < 1e-9 else value
    return f"{value:.8g}"


def scad_vector(values: list[float]) -> str:
    return "[" + ", ".join(number(value) for value in values) + "]"


def rotation(rpy: list[float]) -> list[list[float]]:
    roll, pitch, yaw = rpy
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return [
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ]


def transform(matrix: list[list[float]], vector_: list[float]) -> list[float]:
    return [sum(row[index] * vector_[index] for index in range(3)) for row in matrix]


def inverse_transform(matrix: list[list[float]], vector_: list[float]) -> list[float]:
    return [
        sum(matrix[index][row] * vector_[index] for index in range(3))
        for row in range(3)
    ]


def fixed_mounts(model: ET.Element, parent: str) -> list[list[float]]:
    points = []
    for joint in model.findall("joint"):
        if joint.get("type") != "fixed" or joint.find("parent").get("link") != parent:
            continue
        origin = joint.find("origin")
        points.append(vector(origin, "xyz", 1000.0)[:2])
    return points


def render() -> str:
    arm = ET.parse(SO101).getroot()
    joints = {joint.get("name"): joint for joint in arm.findall("joint")}
    if set(JOINTS) - joints.keys():
        raise ValueError("canonical SO-101 model is missing a required joint")

    names = ", ".join(f'"{name}"' for name in JOINTS)
    xyz = []
    rpy = []
    limits = []
    for name in JOINTS:
        joint = joints[name]
        origin = joint.find("origin")
        limit = joint.find("limit")
        if vector(joint.find("axis"), "xyz") != [0.0, 0.0, 1.0]:
            raise ValueError(f"{name} no longer rotates around local Z")
        xyz.append(vector(origin, "xyz", 1000.0))
        rpy.append([math.degrees(value) for value in vector(origin, "rpy")])
        limits.append(
            [math.degrees(float(limit.get(key))) for key in ("lower", "upper")]
        )

    servo_xyz = []
    servo_rpy = []
    for link_name, joint_name in zip(LINKS, JOINTS, strict=True):
        link = arm.find(f"link[@name='{link_name}']")
        visual = next(
            visual
            for visual in link.findall("visual")
            if "sts3215" in visual.find("geometry/mesh").get("filename").lower()
        )
        servo_origin = visual.find("origin")
        servo_position = vector(servo_origin, "xyz", 1000.0)
        servo_angles = vector(servo_origin, "rpy")
        joint = joints[joint_name]
        joint_position = vector(joint.find("origin"), "xyz", 1000.0)
        joint_angles = vector(joint.find("origin"), "rpy")
        shaft_position = [
            servo_position[index]
            + transform(rotation(servo_angles), SERVO_SHAFT)[index]
            for index in range(3)
        ]
        if math.dist(shaft_position, joint_position) > 0.05:
            raise ValueError(f"{link_name} servo shaft no longer matches {joint_name}")
        servo_axis = transform(rotation(servo_angles), [0.0, 0.0, 1.0])
        joint_axis = transform(rotation(joint_angles), [0.0, 0.0, 1.0])
        if abs(sum(a * b for a, b in zip(servo_axis, joint_axis, strict=True))) < 0.999:
            raise ValueError(f"{link_name} servo axis no longer matches {joint_name}")
        servo_xyz.append(servo_position)
        servo_rpy.append([math.degrees(value) for value in servo_angles])

    lekiwi = ET.parse(LEKIWI).getroot()
    mount = lekiwi.find("joint[@name='so101_mount']")
    if mount is None:
        raise ValueError("LeKiwi Xacro is missing so101_mount")
    mount_origin = mount.find("origin")
    mount_position = vector(mount_origin, "xyz", 1000.0)
    mount_angles = vector(mount_origin, "rpy")
    arm_base_mounts = [
        inverse_transform(
            rotation(mount_angles),
            [
                point[0] - mount_position[0],
                point[1] - mount_position[1],
                -mount_position[2],
            ],
        )[:2]
        for point in ARM_PLATE_HOLES
    ]
    lower_mounts = fixed_mounts(lekiwi, "base_plate_layer1-v5")
    upper_mounts = fixed_mounts(lekiwi, "base_plate_layer2-v3")

    lines = [
        "// Generated by generate_kinematics.py; do not edit.",
        f"joint_names = [{names}];",
        "joint_xyz = [" + ", ".join(scad_vector(values) for values in xyz) + "];",
        "joint_rpy = [" + ", ".join(scad_vector(values) for values in rpy) + "];",
        "joint_limits = [" + ", ".join(scad_vector(values) for values in limits) + "];",
        "servo_xyz = [" + ", ".join(scad_vector(values) for values in servo_xyz) + "];",
        "servo_rpy = [" + ", ".join(scad_vector(values) for values in servo_rpy) + "];",
        f"arm_mount_xyz = {scad_vector(mount_position)};",
        f"arm_mount_rpy = {scad_vector([math.degrees(value) for value in mount_angles])};",
        "arm_base_mounts = ["
        + ", ".join(scad_vector(point) for point in arm_base_mounts)
        + "];",
        "base_lower_mounts = ["
        + ", ".join(scad_vector(point) for point in lower_mounts)
        + "];",
        "base_upper_mounts = ["
        + ", ".join(scad_vector(point) for point in upper_mounts)
        + "];",
        "function joint_index(name) = search([name], joint_names)[0];",
        "function joint_position(name) = joint_xyz[joint_index(name)];",
        "function joint_rotation(name) = joint_rpy[joint_index(name)];",
        "function joint_range(name) = joint_limits[joint_index(name)];",
        "function servo_position(name) = servo_xyz[joint_index(name)];",
        "function servo_rotation(name) = servo_rpy[joint_index(name)];",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail if generated output is stale"
    )
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != expected:
            raise SystemExit(f"stale generated file: run {Path(__file__).name}")
        print(f"verified {OUTPUT.relative_to(ROOT)}")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(expected)
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
