"""Check that a generated Xacro preserves the baseline URDF semantics."""

import json
import sys
import subprocess
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
subprocess.run(
    ["xacro", str(generated_path)], check=True, stdout=subprocess.DEVNULL
)
generated_root = ET.parse(generated_path).getroot()
baseline_root = ET.parse(sys.argv[1]).getroot()
mount_spec = json.loads(
    (generated_path.parents[1] / "cad/accessories/sensor_mount_spec.json").read_text()
)
links = {link.get("name"): link for link in generated_root.findall("link")}
joints = {joint.get("name"): joint for joint in generated_root.findall("joint")}
if not ACCESSORY_LINKS <= links.keys() or not ACCESSORY_JOINTS <= joints.keys():
    raise SystemExit("generated Xacro is missing a sensor accessory")
expected_joints = {
    "astra_pro_compact_mount_joint": (
        "base_plate_layer2-v3", "astra_pro_compact_mount",
        mount_spec["astra"]["mount_origin_m"], mount_spec["astra"]["mount_rpy_rad"],
    ),
    "robotskin_lidar_mount_joint": (
        "base_plate_layer2-v3", "robotskin_lidar_mount",
        mount_spec["lidar"]["mount_origin_m"], mount_spec["lidar"]["mount_rpy_rad"],
    ),
    "ld06_body_mount": (
        "robotskin_lidar_mount", "ld06_body",
        mount_spec["lidar"]["body_center_m"], [0, 0, 0],
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
        or any(abs(actual - expected) > 1e-12
               for actual, expected in zip(map(float, origin.get("xyz").split()), xyz))
        or any(abs(actual - expected) > 1e-12
               for actual, expected in zip(map(float, origin.get("rpy").split()), rpy))
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
# The SO-101 visual override deliberately paints all its parts yellow. Restore
# only this explicitly validated presentation override for the structural
# baseline comparison.
yellow = generated_root.find("material[@name='so101_yellow']/color")
assert yellow is not None and yellow.get("rgba") == "1.0 0.82 0.12 1.0"
for link in generated_root.findall("link"):
    if not link.get("name", "").startswith("so101_"):
        continue
    baseline_visuals = baseline_links[link.get("name")].findall("visual")
    visuals = link.findall("visual")
    assert len(visuals) == len(baseline_visuals)
    for visual, baseline_visual in zip(visuals, baseline_visuals):
        assert visual.find("material").get("name") == "so101_yellow"
        visual.find("material").set("name", baseline_visual.find("material").get("name"))
for material in list(generated_root.findall("material")):
    if material.get("name") == "so101_yellow":
        generated_root.remove(material)
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
