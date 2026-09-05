"""Check that a generated Xacro preserves the baseline URDF semantics."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


XACRO_PROPERTY = "{http://www.ros.org/wiki/xacro}property"
ACCESSORY_LINKS = {"astra_pro_compact_mount", "robotskin_lidar_mount", "ld06_body"}
ACCESSORY_JOINTS = {
    "astra_pro_compact_mount_joint",
    "robotskin_lidar_mount_joint",
    "ld06_body_mount",
}


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
        # Native part 8 retains the official mesh frame and is checked against
        # its STEP reference by test_so101_wrist.py.
        attributes["filename"] = attributes["filename"].replace(
            "so101/native_wrist_flex.stl", "so101/wrist_roll_pitch_so101_v2.stl"
        )
    children = [normalise(child) for child in element]
    return (
        element.tag,
        tuple(sorted(attributes.items())),
        tuple(child for child in children if child is not None),
    )


if len(sys.argv) != 3:
    raise SystemExit("usage: verify_xacro.py BASELINE.urdf GENERATED.urdf.xacro")

generated_path = Path(sys.argv[2])
generated_root = ET.parse(generated_path).getroot()
baseline_root = ET.parse(sys.argv[1]).getroot()
links = {link.get("name"): link for link in generated_root.findall("link")}
joints = {joint.get("name"): joint for joint in generated_root.findall("joint")}
if not ACCESSORY_LINKS <= links.keys() or not ACCESSORY_JOINTS <= joints.keys():
    raise SystemExit("generated Xacro is missing a sensor accessory")
expected_joints = {
    "astra_pro_compact_mount_joint": (
        "base_plate_layer2-v3", "astra_pro_compact_mount", "0 0.08 0.007", "0 0 0"
    ),
    "robotskin_lidar_mount_joint": (
        "base_plate_layer2-v3", "robotskin_lidar_mount", "0.0 -0.115 0.007", "0 0 -1.5707963267948966"
    ),
    "ld06_body_mount": (
        "robotskin_lidar_mount", "ld06_body", "0.02 -0.005 0.012", "0 0 0"
    ),
}
for name, (parent, child, xyz, rpy) in expected_joints.items():
    joint = joints.get(name)
    origin = joint.find("origin") if joint is not None else None
    if (
        joint is None
        or joint.find("parent").get("link") != parent
        or joint.find("child").get("link") != child
        or origin is None
        or origin.get("xyz") != xyz
        or origin.get("rpy") != rpy
    ):
        raise SystemExit(f"{name}: unexpected physical mount pose")
# The arm source is unchanged; only its checked fixed mounting pose supersedes
# the legacy baseline pose.
baseline_joint = baseline_root.find("joint[@name='so101_mount']")
baseline_joint.find("origin").attrib = dict(
    joints["so101_mount"].find("origin").attrib
)
removed = {"Bottom-V2-v3", "Top-V2-v2"}
assert not removed & links.keys(), "removed Pi case must not return on export"
for element in list(baseline_root):
    if (element.tag == "link" and element.get("name") in removed) or (
        element.tag == "joint" and element.find("child").get("link") in removed
    ):
        baseline_root.remove(element)
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
baseline = normalise(baseline_root)
generated = normalise(generated_root)
if baseline != generated:
    raise SystemExit("generated Xacro does not preserve baseline URDF semantics")
print("generated Xacro preserves baseline URDF semantics")
