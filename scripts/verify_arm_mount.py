"""Check that SO-101 integration preserves the editable assembly's shoulder datum."""

import copy
import xml.etree.ElementTree as ET

import FreeCAD as App

from scripts.cad_utils import urdf_matrix
from scripts.replace_arm_with_so101 import replace_arm, shoulder_basis


document = App.openDocument("cad/assembly/LeKiwi.FCStd")
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
    parents = {joint.find("child").get("link"): joint for joint in root.findall("joint")}
    frame = root.find("joint[@name='arm_shoulder_pan']/child").get("link")
    result = App.Matrix()
    while frame != "base_plate_layer2-v3":
        joint = parents[frame]
        result = urdf_matrix(joint.find("origin")).multiply(result)
        frame = joint.find("parent").get("link")
    return result


for shift in (0, 0.02):
    original = copy.deepcopy(model)
    origin = original.find("joint[@name='base_plate_layer2-v3_Rigid-42']/origin")
    xyz = list(map(float, origin.get("xyz").split()))
    xyz[0] += shift
    origin.set("xyz", " ".join(map(str, xyz)))
    expected = shoulder_pose(original)
    expected_basis = shoulder_basis(original, "arm_", "base_plate_layer2-v3")
    replace_arm(original)
    actual = shoulder_pose(original)
    assert all(abs(getattr(actual, key) - getattr(expected, key)) < 1e-6
               for key in ("A14", "A24", "A34"))
    actual_basis = shoulder_basis(original, "arm_", "base_plate_layer2-v3")
    assert all(abs(a - b) < 1e-6 for a, b in zip(actual_basis.A, expected_basis.A))

generated = ET.parse("URDF/LeKiwi.urdf.xacro").getroot()
assert all(abs(getattr(shoulder_pose(generated), key) - getattr(shoulder_pose(model), key)) < 1e-6
           for key in ("A14", "A24", "A34"))
assert all(abs(a - b) < 1e-6 for a, b in zip(
    shoulder_basis(generated, "arm_", "base_plate_layer2-v3").A,
    shoulder_basis(model, "arm_", "base_plate_layer2-v3").A,
))
print("SO-101 shoulder datum matches CAD and follows assembly edits")
