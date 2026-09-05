#!/usr/bin/env python3
"""Replace the legacy SO-100 subtree with the pinned SO-101 follower model."""

from __future__ import annotations

import copy
import math
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SO101_URDF = ROOT / "cad/upstream/SO-ARM100/Simulation/SO101/so101_new_calib.urdf"
OLD_MOUNT_JOINT = "base_plate_layer2-v3_Rigid-42"
LINK_NAMES = {
    "base_link": "so101_base_link",
    "shoulder_link": "so101_shoulder_link",
    "upper_arm_link": "so101_upper_arm_link",
    "lower_arm_link": "so101_lower_arm_link",
    "wrist_link": "so101_wrist_link",
    "gripper_link": "so101_gripper_link",
    "gripper_frame_link": "so101_gripper_frame_link",
    "moving_jaw_so101_v1_link": "so101_moving_jaw_link",
}
JOINT_NAMES = {
    "shoulder_pan": "arm_shoulder_pan",
    "shoulder_lift": "arm_shoulder_lift",
    "elbow_flex": "arm_elbow_flex",
    "wrist_flex": "arm_wrist_flex",
    "wrist_roll": "arm_wrist_roll",
    "gripper": "arm_gripper",
    "gripper_frame_joint": "so101_gripper_frame_joint",
}


def descendants(root: ET.Element, start: str) -> set[str]:
    children = defaultdict(list)
    for joint in root.findall("joint"):
        children[joint.find("parent").get("link")].append(
            joint.find("child").get("link")
        )
    found = {start}
    pending = [start]
    while pending:
        for child in children[pending.pop()]:
            if child not in found:
                found.add(child)
                pending.append(child)
    return found


def joint_pose(model, name, parent):
    import FreeCAD as App
    from scripts.cad_utils import urdf_matrix

    parents = {joint.find("child").get("link"): joint for joint in model.findall("joint")}
    joint = model.find(f"joint[@name='{name}']")
    if joint is None:
        raise ValueError(f"missing mounting datum joint: {name}")
    frame, placement, visited = joint.find("child").get("link"), App.Matrix(), set()
    while frame != parent:
        if frame in visited or frame not in parents:
            raise ValueError(f"{name} is not connected to {parent}")
        visited.add(frame)
        joint = parents[frame]
        placement = urdf_matrix(joint.find("origin")).multiply(placement)
        frame = joint.find("parent").get("link")
    return placement


def shoulder_basis(model, prefix, parent):
    import FreeCAD as App

    axes = []
    for name in (prefix + "shoulder_lift", prefix + "shoulder_pan"):
        axis = App.Vector(*map(float, model.find(f"joint[@name='{name}']/axis").get("xyz").split()))
        axes.append(App.Rotation(joint_pose(model, name, parent)).multVec(axis).normalize())
    x, z = axes
    y = z.cross(x).normalize()
    x = y.cross(z).normalize()
    result = App.Matrix()
    for column, vector in enumerate((x, y, z), 1):
        for row, value in enumerate((vector.x, vector.y, vector.z), 1):
            setattr(result, f"A{row}{column}", value)
    return result


def replace_arm(model: ET.Element) -> None:
    mount = model.find(f"joint[@name='{OLD_MOUNT_JOINT}']")
    if mount is None or mount.find("child").get("link") != "Base_08q-v1":
        raise ValueError("input does not contain the expected SO-100 arm mount")
    # Base-part origins are not interchangeable. Preserve the assembly's
    # shoulder centre and bending plane. The installed SO-101 faces outward
    # on the fixed-camera side (CAD +Y), opposite the legacy reference arm.
    # This is mounting geometry, not a motor-zero calibration correction.

    source = ET.parse(SO101_URDF).getroot()
    target_parent = mount.find("parent").get("link")
    target_pan = joint_pose(model, "arm_shoulder_pan", target_parent)
    source_pan = joint_pose(source, "shoulder_pan", "base_link")
    import FreeCAD as App
    placement = shoulder_basis(model, "arm_", target_parent).multiply(
        App.Rotation(App.Vector(0, 0, 1), 180).toMatrix()
    ).multiply(
        shoulder_basis(source, "", "base_link").inverse()
    )
    offset = placement.multVec(App.Vector(source_pan.A14, source_pan.A24, source_pan.A34))
    placement.A14, placement.A24, placement.A34 = (
        target_pan.A14 - offset.x, target_pan.A24 - offset.y, target_pan.A34 - offset.z
    )
    yaw, pitch, roll = App.Rotation(placement).getYawPitchRoll()
    mount_origin = {
        "xyz": " ".join(f"{value / 1000:.12g}" for value in (placement.A14, placement.A24, placement.A34)),
        "rpy": " ".join(f"{math.radians(value):.12g}" for value in (roll, pitch, yaw)),
    }
    old_links = descendants(model, "Base_08q-v1")
    for link in list(model.findall("link")):
        if link.get("name") in old_links:
            model.remove(link)
    for joint in list(model.findall("joint")):
        if joint.find("child").get("link") in old_links:
            model.remove(joint)

    existing_materials = {
        material.get("name") for material in model.findall("material")
    }
    for material in source.findall("material"):
        if material.get("name") not in existing_materials:
            model.append(copy.deepcopy(material))

    xacro_model = model.find("{http://www.ros.org/wiki/xacro}property") is not None
    mesh_prefix = "${mesh_dir}/so101/" if xacro_model else "meshes/so101/"
    for source_link in source.findall("link"):
        link = copy.deepcopy(source_link)
        link.set("name", LINK_NAMES[source_link.get("name")])
        for invalid_origin in link.findall("origin"):
            link.remove(invalid_origin)
        if source_link.get("name") == "gripper_frame_link":
            link.remove(link.find("inertial"))
        for mesh in link.findall(".//mesh"):
            name = Path(mesh.get("filename")).name
            if name == "wrist_roll_pitch_so101_v2.stl":
                name = "native_wrist_flex.stl"
            mesh.set("filename", mesh_prefix + name)
        model.append(link)

    mount = ET.Element("joint", {"name": "so101_mount", "type": "fixed"})
    ET.SubElement(
        mount,
        "origin",
        mount_origin,
    )
    ET.SubElement(mount, "parent", {"link": target_parent})
    ET.SubElement(mount, "child", {"link": "so101_base_link"})
    model.append(mount)

    for source_joint in source.findall("joint"):
        joint = copy.deepcopy(source_joint)
        joint.set("name", JOINT_NAMES[source_joint.get("name")])
        joint.find("parent").set("link", LINK_NAMES[joint.find("parent").get("link")])
        joint.find("child").set("link", LINK_NAMES[joint.find("child").get("link")])
        model.append(joint)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: replace_arm_with_so101.py INPUT.urdf OUTPUT.urdf")
    source, output = map(Path, sys.argv[1:])
    tree = ET.parse(source)
    replace_arm(tree.getroot())
    # Refresh the official mesh bundle every export, including changed upstream
    # assets. Previously only the XML was regenerated and old meshes survived.
    assets = SO101_URDF.parent / "assets"
    mesh_files = {Path(mesh.get("filename")).name for mesh in tree.findall(".//mesh")
                  if "/so101/" in mesh.get("filename", "")}
    contents = {name: (
        ROOT / "cad/generated/so101" / name if name == "native_wrist_flex.stl"
        else assets / name
    ).read_bytes() for name in mesh_files}
    for name, content in contents.items():
        destination = output.parent / "meshes/so101" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    ET.indent(tree, space="    ")
    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding="utf-8", xml_declaration=True)
    print(f"replaced SO-100 arm with SO-101 follower in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
