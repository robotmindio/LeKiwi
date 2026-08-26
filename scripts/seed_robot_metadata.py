"""Embed the validated URDF link and joint data in a FreeCAD document."""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import FreeCAD as App


def object_name(prefix, name):
    return prefix + re.sub(r"[^0-9A-Za-z_]", "_", name)


def attr(element, name, default=""):
    return element.get(name, default) if element is not None else default


if len(sys.argv) != 4:
    raise SystemExit("usage: seed_robot_metadata.py REFERENCE.FCStd INPUT.urdf OUTPUT.FCStd")

reference, urdf, output = map(Path, sys.argv[1:])
if not reference.is_file() or not urdf.is_file():
    raise SystemExit("reference FreeCAD document and URDF must exist")

document = App.openDocument(str(reference))
if document.getObject("LeKiwiRobot"):
    document.removeObject("LeKiwiRobot")

robot = document.addObject("App::DocumentObjectGroup", "LeKiwiRobot")
robot.Label = "LeKiwi robot metadata"
links = document.addObject("App::DocumentObjectGroup", "LeKiwiLinks")
joints = document.addObject("App::DocumentObjectGroup", "LeKiwiJoints")
robot.addObject(links)
robot.addObject(joints)

root = ET.parse(urdf).getroot()
for link_xml in root.findall("link"):
    name = link_xml.get("name")
    link = document.addObject("App::FeaturePython", object_name("Link_", name))
    link.Label = name
    link.addProperty("App::PropertyString", "UrdfName", "ROS")
    link.UrdfName = name
    link.addProperty("App::PropertyLinkListGlobal", "CadParts", "CAD")
    link.addProperty("App::PropertyBool", "UseCadMass", "CAD")
    link.UseCadMass = False

    inertial = link_xml.find("inertial")
    origin = inertial.find("origin") if inertial is not None else None
    mass = inertial.find("mass") if inertial is not None else None
    inertia = inertial.find("inertia") if inertial is not None else None
    for property_name, value in (
        ("InertialXYZ", attr(origin, "xyz", "0 0 0")),
        ("InertialRPY", attr(origin, "rpy", "0 0 0")),
        ("Mass", attr(mass, "value", "0")),
        ("Ixx", attr(inertia, "ixx", "0")),
        ("Iyy", attr(inertia, "iyy", "0")),
        ("Izz", attr(inertia, "izz", "0")),
        ("Ixy", attr(inertia, "ixy", "0")),
        ("Ixz", attr(inertia, "ixz", "0")),
        ("Iyz", attr(inertia, "iyz", "0")),
    ):
        link.addProperty("App::PropertyString", property_name, "Inertial")
        setattr(link, property_name, value)

    for kind in ("visual", "collision"):
        element = link_xml.find(kind)
        origin = element.find("origin") if element is not None else None
        mesh = element.find("geometry/mesh") if element is not None else None
        prefix = kind.title()
        for property_name, value in (
            (prefix + "Name", attr(element, "name", name + "_" + kind)),
            (prefix + "XYZ", attr(origin, "xyz", "0 0 0")),
            (prefix + "RPY", attr(origin, "rpy", "0 0 0")),
            (prefix + "Mesh", attr(mesh, "filename")),
            (prefix + "Scale", attr(mesh, "scale", "1 1 1")),
        ):
            link.addProperty("App::PropertyString", property_name, "Geometry")
            setattr(link, property_name, value)
    links.addObject(link)

for joint_xml in root.findall("joint"):
    name = joint_xml.get("name")
    joint = document.addObject("App::FeaturePython", object_name("Joint_", name))
    joint.Label = name
    origin = joint_xml.find("origin")
    axis = joint_xml.find("axis")
    limit = joint_xml.find("limit")
    for property_name, value in (
        ("UrdfName", name),
        ("JointType", joint_xml.get("type")),
        ("Parent", attr(joint_xml.find("parent"), "link")),
        ("Child", attr(joint_xml.find("child"), "link")),
        ("OriginXYZ", attr(origin, "xyz", "0 0 0")),
        ("OriginRPY", attr(origin, "rpy", "0 0 0")),
        ("Axis", attr(axis, "xyz", "0 0 1")),
        ("Lower", attr(limit, "lower")),
        ("Upper", attr(limit, "upper")),
        ("Effort", attr(limit, "effort")),
        ("Velocity", attr(limit, "velocity")),
    ):
        joint.addProperty("App::PropertyString", property_name, "ROS")
        setattr(joint, property_name, value)
    joint.addProperty("App::PropertyBool", "HasAxis", "ROS")
    joint.HasAxis = axis is not None
    joint.addProperty("App::PropertyBool", "HasLimit", "ROS")
    joint.HasLimit = limit is not None
    joints.addObject(joint)

document.recompute()
output.parent.mkdir(parents=True, exist_ok=True)
document.saveAs(str(output))
print(f"saved {output} with {len(links.Group)} links and {len(joints.Group)} joints")
