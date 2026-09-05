#!/usr/bin/env python3
"""Replace the legacy SO-100 subtree with the pinned SO-101 follower model."""

from __future__ import annotations

import copy
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SO101_URDF = ROOT / "cad/upstream/SO-ARM100/Simulation/SO101/so101_new_calib.urdf"
OLD_MOUNT_JOINT = "base_plate_layer2-v3_Rigid-42"
SO101_MOUNT_XYZ = "0.04 0.08 0.007"
SO101_MOUNT_RPY = "0 0 0"
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


def replace_arm(model: ET.Element) -> None:
    mount = model.find(f"joint[@name='{OLD_MOUNT_JOINT}']")
    if mount is None or mount.find("child").get("link") != "Base_08q-v1":
        raise ValueError("input does not contain the expected SO-100 arm mount")
    old_links = descendants(model, "Base_08q-v1")
    for link in list(model.findall("link")):
        if link.get("name") in old_links:
            model.remove(link)
    for joint in list(model.findall("joint")):
        if joint.find("child").get("link") in old_links:
            model.remove(joint)

    source = ET.parse(SO101_URDF).getroot()
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
            mesh.set("filename", mesh_prefix + Path(mesh.get("filename")).name)
        model.append(link)

    mount = ET.Element("joint", {"name": "so101_mount", "type": "fixed"})
    ET.SubElement(
        mount,
        "origin",
        {"xyz": SO101_MOUNT_XYZ, "rpy": SO101_MOUNT_RPY},
    )
    ET.SubElement(mount, "parent", {"link": "base_plate_layer2-v3"})
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
    ET.indent(tree, space="    ")
    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding="utf-8", xml_declaration=True)
    print(f"replaced SO-100 arm with SO-101 follower in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
