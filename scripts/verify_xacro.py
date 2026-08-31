"""Check that a generated Xacro preserves the baseline URDF semantics."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


XACRO_PROPERTY = "{http://www.ros.org/wiki/xacro}property"
ACCESSORY_LINKS = {"robotskin_lidar_mount", "ld06_body"}
ACCESSORY_JOINTS = {"robotskin_lidar_mount_joint", "ld06_body_mount"}


def normalise(element):
    if element.tag == XACRO_PROPERTY:
        return None
    attributes = dict(element.attrib)
    if element.tag == "mesh":
        attributes["filename"] = attributes["filename"].replace(
            "${mesh_dir}/", "meshes/"
        )
        attributes["filename"] = attributes["filename"].replace(
            "meshes/reauthored/", "meshes/"
        )
    children = [normalise(child) for child in element]
    return (
        element.tag,
        tuple(sorted(attributes.items())),
        tuple(child for child in children if child is not None),
    )


if len(sys.argv) != 3:
    raise SystemExit("usage: verify_xacro.py BASELINE.urdf GENERATED.urdf.xacro")

baseline = normalise(ET.parse(sys.argv[1]).getroot())
generated_path = Path(sys.argv[2])
generated_root = ET.parse(generated_path).getroot()
baseline_root = ET.parse(sys.argv[1]).getroot()
links = {link.get("name"): link for link in generated_root.findall("link")}
joints = {joint.get("name"): joint for joint in generated_root.findall("joint")}
if not ACCESSORY_LINKS <= links.keys() or not ACCESSORY_JOINTS <= joints.keys():
    raise SystemExit("generated Xacro is missing the RobotSkin LD06 accessory")
if (
    joints["robotskin_lidar_mount_joint"].find("parent").get("link")
    != "base_plate_layer1-v5"
):
    raise SystemExit("RobotSkin lidar mount must remain attached to the base plate")
if joints["ld06_body_mount"].find("parent").get("link") != "robotskin_lidar_mount":
    raise SystemExit("LD06 body must remain attached to its RobotSkin mount")
for link in list(generated_root.findall("link")):
    if link.get("name") in ACCESSORY_LINKS:
        generated_root.remove(link)
for joint in list(generated_root.findall("joint")):
    if joint.get("name") in ACCESSORY_JOINTS:
        generated_root.remove(joint)
baseline_links = {link.get("name"): link for link in baseline_root.findall("link")}
for link in generated_root.findall("link"):
    for kind in ("visual", "collision"):
        mesh = link.find(f"{kind}/geometry/mesh")
        if mesh is not None and mesh.get("filename", "").startswith(
            "${mesh_dir}/reauthored/"
        ):
            origin = link.find(f"{kind}/origin")
            if (
                origin is None
                or origin.get("xyz") != "0 0 0"
                or origin.get("rpy") != "0 0 0"
            ):
                raise SystemExit(
                    f"{link.get('name')}: reauthored {kind} is not in the link frame"
                )
            baseline_origin = baseline_links[link.get("name")].find(f"{kind}/origin")
            origin.attrib = dict(baseline_origin.attrib)
for mesh in generated_root.findall(".//mesh"):
    filename = mesh.get("filename", "")
    if filename.startswith("${mesh_dir}/reauthored/"):
        output = (
            generated_path.parent / "meshes" / "reauthored" / filename.rsplit("/", 1)[1]
        )
        if not output.is_file() or output.stat().st_size == 0:
            raise SystemExit(f"missing reauthored mesh: {output}")
generated = normalise(generated_root)
if baseline != generated:
    raise SystemExit("generated Xacro does not preserve baseline URDF semantics")
print("generated Xacro preserves baseline URDF semantics")
