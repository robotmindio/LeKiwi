"""Check that SO-101 integration preserves the editable assembly's shoulder datum."""

import copy
import sys
import xml.etree.ElementTree as ET

import FreeCAD as App

from scripts.cad_utils import SO101_YELLOW_RGBA, require
from scripts.replace_arm_with_so101 import joint_pose, replace_arm, shoulder_basis


assembly = sys.argv[1] if len(sys.argv) > 1 else "cad/assembly/LeKiwi.FCStd"
generated_path = sys.argv[2] if len(sys.argv) > 2 else "URDF/LeKiwi.urdf.xacro"
document = App.openDocument(assembly)
model = ET.Element("robot")
for item in document.getObject("LeKiwiLinks").Group:
    ET.SubElement(model, "link", name=item.UrdfName)
for item in document.getObject("LeKiwiJoints").Group:
    joint = ET.SubElement(model, "joint", name=item.UrdfName, type=item.JointType)
    ET.SubElement(joint, "parent", link=item.Parent)
    ET.SubElement(joint, "child", link=item.Child)
    ET.SubElement(joint, "origin", xyz=item.OriginXYZ, rpy=item.OriginRPY)
    ET.SubElement(joint, "axis", xyz=item.Axis)


def shoulder_pose(root):
    return joint_pose(root, "arm_shoulder_pan", "base_plate_layer2-v3")


for shift in (0, 0.02):
    original = copy.deepcopy(model)
    origin = original.find("joint[@name='base_plate_layer2-v3_Rigid-42']/origin")
    xyz = list(map(float, origin.get("xyz").split()))
    xyz[0] += shift
    origin.set("xyz", " ".join(map(str, xyz)))
    expected = shoulder_pose(original)
    expected_basis = shoulder_basis(original, "arm_", "base_plate_layer2-v3").multiply(
        App.Rotation(App.Vector(0, 0, 1), 180).toMatrix()
    )
    replace_arm(original)
    actual = shoulder_pose(original)
    require(
        all(abs(getattr(actual, key) - getattr(expected, key)) < 1e-6
            for key in ("A14", "A24", "A34")),
        "shoulder datum shifted",
    )
    actual_basis = shoulder_basis(original, "arm_", "base_plate_layer2-v3")
    require(
        all(abs(a - b) < 1e-6 for a, b in zip(actual_basis.A, expected_basis.A)),
        "shoulder basis shifted",
    )
    # User-defined forward is the arm/fixed-camera side, CAD +Y (ROS +X).
    tool = joint_pose(original, "so101_gripper_frame_joint", "base_plate_layer2-v3")
    require(tool.A24 > actual.A24 + 100, "arm does not face outward")

generated = ET.parse(generated_path).getroot()
yellow = generated.find("material[@name='so101_yellow']/color")
require(
    yellow is not None and yellow.get("rgba") == SO101_YELLOW_RGBA,
    "so101_yellow material must match the validated override color",
)
require(
    all(visual.find("material").get("name") == "so101_yellow"
        for link in generated.findall("link") if link.get("name").startswith("so101_")
        for visual in link.findall("visual")),
    "every so101_ visual must use the so101_yellow override",
)
require(
    all(abs(getattr(shoulder_pose(generated), key) - getattr(shoulder_pose(model), key)) < 1e-6
        for key in ("A14", "A24", "A34")),
    "exported shoulder datum differs from the assembly",
)
require(
    all(abs(a - b) < 1e-6 for a, b in zip(
        shoulder_basis(generated, "arm_", "base_plate_layer2-v3").A,
        shoulder_basis(model, "arm_", "base_plate_layer2-v3").multiply(
            App.Rotation(App.Vector(0, 0, 1), 180).toMatrix()
        ).A,
    )),
    "exported shoulder basis differs from the assembly",
)
print("SO-101 preserves the shoulder datum, faces outward, and follows assembly edits")
