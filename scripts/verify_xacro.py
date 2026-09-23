"""Check that a generated Xacro preserves the baseline URDF semantics."""

import json
import math
import sys
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from cad_utils import PI_CASE_LINKS, SO101_YELLOW_RGBA, require


XACRO_PROPERTY = "{http://www.ros.org/wiki/xacro}property"
ROOT = Path(__file__).resolve().parents[1]
RPI5_LINKS = ("rpi5_through_plate", "rpi5_usb_carrier", "rpi5_table")
ACCESSORY_LINKS = {"astra_pro_compact_mount", "robotskin_lidar_mount", "ld06_body", *RPI5_LINKS}
ACCESSORY_JOINTS = {
    "astra_pro_compact_mount_joint",
    "robotskin_lidar_mount_joint",
    "ld06_body_mount",
    *(name + "_joint" for name in RPI5_LINKS),
}
_chassis_rod_spec = json.loads((ROOT / "cad/chassis_rod_positions.json").read_text())
ROD = _chassis_rod_spec["rod"]
POSITIONS = {name: tuple(xy) for name, xy in _chassis_rod_spec["positions"].items()}


def normalise(element, skip_ids=frozenset()):
    if element.tag == XACRO_PROPERTY:
        return None
    if id(element) in skip_ids:
        # CAD-derived mass/inertia is checked physically in validate_inertial()
        # instead of exact-matched against the baseline, whose <inertial> was
        # never generated from real CAD mass.
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
    children = [normalise(child, skip_ids) for child in element]
    return (
        element.tag,
        tuple(sorted(attributes.items())),
        tuple(child for child in children if child is not None),
    )


def cad_mass_inertial_ids(root, cad_mass_links):
    """id() of every <inertial> element belonging to a UseCadMass link.

    ElementTree elements do not track their parent and the C accelerator does
    not allow tagging them with a custom attribute, so normalise() is told
    which elements to skip by identity instead of by an attribute lookup.
    """
    ids = set()
    for link in root.findall("link"):
        if link.get("name") in cad_mass_links:
            inertial = link.find("inertial")
            if inertial is not None:
                ids.add(id(inertial))
    return ids


def validate_inertial(link_name, inertial):
    """Physically sanity-check a CAD-derived <inertial> block.

    Mass must be positive and finite. The inertia tensor must be symmetric
    positive-definite, and its principal moments must satisfy the rotational
    triangle inequality (each moment no greater than the sum of the other two).
    """
    mass = float(inertial.find("mass").get("value"))
    require(math.isfinite(mass) and mass > 0, f"{link_name}: inertial mass must be positive and finite")
    inertia = inertial.find("inertia")
    ixx, iyy, izz, ixy, ixz, iyz = (
        float(inertia.get(key)) for key in ("ixx", "iyy", "izz", "ixy", "ixz", "iyz")
    )
    require(
        all(math.isfinite(value) for value in (ixx, iyy, izz, ixy, ixz, iyz)),
        f"{link_name}: inertia tensor must be finite",
    )
    matrix = ((ixx, ixy, ixz), (ixy, iyy, iyz), (ixz, iyz, izz))
    # Positive-definiteness via Sylvester's criterion (leading principal minors).
    minors = (
        matrix[0][0],
        matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0],
        (
            matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
            - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
            + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
        ),
    )
    require(
        all(minor > 0 for minor in minors),
        f"{link_name}: inertia tensor is not positive-definite",
    )
    eigenvalues = symmetric_eigenvalues(matrix)
    require(
        all(
            eigenvalues[i] <= eigenvalues[j] + eigenvalues[k] + 1e-9
            for i, j, k in ((0, 1, 2), (1, 0, 2), (2, 0, 1))
        ),
        f"{link_name}: principal moments violate the triangle inequality",
    )


def symmetric_eigenvalues(matrix):
    """Closed-form eigenvalues of a real symmetric 3x3 matrix."""
    a, b, c = matrix[0][0], matrix[1][1], matrix[2][2]
    d, e, f = matrix[0][1], matrix[0][2], matrix[1][2]
    trace = a + b + c
    p2 = d * d + e * e + f * f
    if p2 < 1e-18:
        return sorted((a, b, c))
    q = trace / 3
    p = math.sqrt(((a - q) ** 2 + (b - q) ** 2 + (c - q) ** 2 + 2 * p2) / 6)
    scaled = tuple(
        tuple((matrix[row][col] - (q if row == col else 0)) / p for col in range(3))
        for row in range(3)
    )
    determinant = (
        scaled[0][0] * (scaled[1][1] * scaled[2][2] - scaled[1][2] * scaled[2][1])
        - scaled[0][1] * (scaled[1][0] * scaled[2][2] - scaled[1][2] * scaled[2][0])
        + scaled[0][2] * (scaled[1][0] * scaled[2][1] - scaled[1][1] * scaled[2][0])
    )
    r = max(-1.0, min(1.0, determinant / 2))
    phi = math.acos(r) / 3
    eig1 = q + 2 * p * math.cos(phi)
    eig3 = q + 2 * p * math.cos(phi + 2 * math.pi / 3)
    eig2 = trace - eig1 - eig3
    return sorted((eig1, eig2, eig3))


if len(sys.argv) != 3:
    raise SystemExit("usage: verify_xacro.py BASELINE.urdf GENERATED.urdf.xacro")

generated_path = Path(sys.argv[2])
subprocess.run(["xacro", str(generated_path)], check=True, stdout=subprocess.DEVNULL)
generated_root = ET.parse(generated_path).getroot()
baseline_root = ET.parse(sys.argv[1]).getroot()
mount_spec = json.loads((ROOT / "cad/accessories/sensor_mount_spec.json").read_text())
links = {link.get("name"): link for link in generated_root.findall("link")}
joints = {joint.get("name"): joint for joint in generated_root.findall("joint")}
# Operator-identified chassis holes supersede the legacy rod placements.
by_child = {j.find("child").get("link"): j for j in joints.values()}
rod_poses = {name: [x / 1000, y / 1000, 0] for name, (x, y) in POSITIONS.items()}
x, y = POSITIONS[ROD]
rod_poses["base_plate_layer2-v3"] = [-x / 1000, y / 1000, -0.05]
for child, xyz in rod_poses.items():
    joint = by_child[child]
    require(
        joint.find("parent").get("link")
        == (ROD if child == "base_plate_layer2-v3" else "base_plate_layer1-v5"),
        f"{child}: unexpected rod parent",
    )
    actual = list(map(float, joint.find("origin").get("xyz").split()))
    require(
        len(actual) == 3 and all(abs(a - b) < 1e-12 for a, b in zip(actual, xyz)),
        f"{child}: unexpected rod origin",
    )
    baseline_joint = baseline_root.find(f"joint[@name='{joint.get('name')}']")
    baseline_joint.find("origin").set("xyz", joint.find("origin").get("xyz"))
for child, pose in json.loads(
    (ROOT / "cad/wheel_mount_v2_poses.json").read_text()
).items():
    joint = by_child[child]
    for field in ("xyz", "rpy"):
        actual = list(map(float, joint.find("origin").get(field).split()))
        expected = list(map(float, pose[field].split()))
        require(
            len(actual) == len(expected) == 3
            and all(abs(a - b) < 1e-10 for a, b in zip(actual, expected)),
            f"{child}: unexpected wheel mount {field}",
        )
    baseline_joint = baseline_root.find(f"joint[@name='{joint.get('name')}']")
    baseline_joint.find("origin").attrib = dict(joint.find("origin").attrib)
if not ACCESSORY_LINKS <= links.keys() or not ACCESSORY_JOINTS <= joints.keys():
    raise SystemExit("generated Xacro is missing a sensor accessory")
expected_joints = {
    "astra_pro_compact_mount_joint": (
        "base_plate_layer2-v3",
        "astra_pro_compact_mount",
        mount_spec["astra"]["mount_origin_m"],
        mount_spec["astra"]["mount_rpy_rad"],
    ),
    "robotskin_lidar_mount_joint": (
        "base_plate_layer2-v3",
        "robotskin_lidar_mount",
        mount_spec["lidar"]["mount_origin_m"],
        mount_spec["lidar"]["mount_rpy_rad"],
    ),
    "ld06_body_mount": (
        "robotskin_lidar_mount",
        "ld06_body",
        mount_spec["lidar"]["body_center_m"],
        [0, 0, 0],
    ),
    "rpi5_through_plate_joint": (
        "base_plate_layer2-v3",
        "rpi5_through_plate",
        mount_spec["rpi5"]["plate_origin_m"],
        mount_spec["rpi5"]["plate_rpy_rad"],
    ),
    "rpi5_usb_carrier_joint": (
        "rpi5_through_plate",
        "rpi5_usb_carrier",
        mount_spec["rpi5"]["carrier_origin_m"],
        [0, 0, 0],
    ),
    "rpi5_table_joint": (
        "rpi5_through_plate",
        "rpi5_table",
        mount_spec["rpi5"]["table_origin_m"],
        [0, 0, 0],
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
        or any(
            abs(actual - expected) > 1e-12
            for actual, expected in zip(map(float, origin.get("xyz").split()), xyz)
        )
        or any(
            abs(actual - expected) > 1e-12
            for actual, expected in zip(map(float, origin.get("rpy").split()), rpy)
        )
    ):
        raise SystemExit(f"{name}: unexpected physical mount pose")
# The arm source is unchanged; only its checked fixed mounting pose supersedes
# the legacy baseline pose.
baseline_joint = baseline_root.find("joint[@name='so101_mount']")
baseline_joint.find("origin").attrib = dict(joints["so101_mount"].find("origin").attrib)
require(
    not PI_CASE_LINKS & links.keys(), "removed Pi case must not return on export"
)
for element in list(baseline_root):
    if (element.tag == "link" and element.get("name") in PI_CASE_LINKS) or (
        element.tag == "joint" and element.find("child").get("link") in PI_CASE_LINKS
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
require(
    yellow is not None and yellow.get("rgba") == SO101_YELLOW_RGBA,
    "so101_yellow material must match the validated override color",
)
for link in generated_root.findall("link"):
    if not link.get("name", "").startswith("so101_"):
        continue
    baseline_visuals = baseline_links[link.get("name")].findall("visual")
    visuals = link.findall("visual")
    require(
        len(visuals) == len(baseline_visuals),
        f"{link.get('name')}: visual count mismatch",
    )
    for visual, baseline_visual in zip(visuals, baseline_visuals):
        require(
            visual.find("material").get("name") == "so101_yellow",
            f"{link.get('name')}: expected the so101_yellow override",
        )
        visual.find("material").set(
            "name", baseline_visual.find("material").get("name")
        )
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

# Links exported with attach_cad_part.py's UseCadMass=True get a real
# CAD-derived <inertial> that will never match the baseline URDF's fallback
# values. export_xacro.py records those link names alongside its output so
# this check can validate them physically instead of by exact match.
cad_mass_links_path = (
    generated_path.resolve().parents[1] / "cad" / "generated" / "cad_mass_links.json"
)
cad_mass_links = (
    frozenset(json.loads(cad_mass_links_path.read_text()))
    if cad_mass_links_path.is_file()
    else frozenset()
)
for link_name in cad_mass_links:
    link = links.get(link_name)
    if link is None:
        raise SystemExit(f"{link_name}: recorded as UseCadMass but missing from export")
    inertial = link.find("inertial")
    if inertial is None:
        raise SystemExit(f"{link_name}: UseCadMass link must have an <inertial>")
    validate_inertial(link_name, inertial)

skip_ids = cad_mass_inertial_ids(baseline_root, cad_mass_links) | cad_mass_inertial_ids(
    generated_root, cad_mass_links
)
baseline = normalise(baseline_root, skip_ids)
generated = normalise(generated_root, skip_ids)
if baseline != generated:
    raise SystemExit("generated Xacro does not preserve baseline URDF semantics")
print("generated Xacro preserves baseline URDF semantics")
