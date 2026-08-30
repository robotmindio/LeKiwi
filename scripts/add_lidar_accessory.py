"""Add the RobotSkin LD06 mount and lidar to the editable LeKiwi assembly."""

import re
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import Part


if len(sys.argv) != 4:
    raise SystemExit("usage: add_lidar_accessory.py ASSEMBLY.FCStd SOURCE.scad MOUNT.stl")


assembly_path, source_path, mount_path = map(Path, sys.argv[1:])
if not source_path.is_file():
    raise RuntimeError(f"missing RobotSkin OpenSCAD source: {source_path}")
if not mount_path.is_file():
    raise RuntimeError(f"missing generated RobotSkin lidar mesh: {mount_path}")

# CAD coordinates: +Y is forward.  The mount's LD06 centre is (20, -5) mm;
# this places its scan centre 90 mm forward and 70 mm right in ROS base_link.
MOUNT_ORIGIN = (0.050, 0.095, 0)
LD06_CENTER = (0.020, -0.005, 0.012)
LD06_RADIUS_MM = 24.5
LD06_HEIGHT_MM = 39


def object_name(prefix, name):
    return prefix + re.sub(r"[^0-9A-Za-z_]", "_", name)


def remove(document, name):
    item = document.getObject(name)
    if item:
        document.removeObject(item.Name)


def add_link(document, links, name, part):
    link = document.addObject("App::FeaturePython", object_name("Link_", name))
    link.Label = name
    link.addProperty("App::PropertyString", "UrdfName", "ROS")
    link.UrdfName = name
    link.addProperty("App::PropertyLinkListGlobal", "CadParts", "CAD")
    link.CadParts = [part]
    link.addProperty("App::PropertyBool", "UseCadMass", "CAD")
    link.UseCadMass = False
    for property_name, value in (
        ("InertialXYZ", "0 0 0"), ("InertialRPY", "0 0 0"), ("Mass", "0"),
        ("Ixx", "0"), ("Iyy", "0"), ("Izz", "0"), ("Ixy", "0"),
        ("Ixz", "0"), ("Iyz", "0"), ("VisualName", name + "_visual"),
        ("VisualXYZ", "0 0 0"), ("VisualRPY", "0 0 0"), ("VisualMesh", ""),
        ("VisualScale", "0.001 0.001 0.001"), ("CollisionName", name + "_collision"),
        ("CollisionXYZ", "0 0 0"), ("CollisionRPY", "0 0 0"),
        ("CollisionMesh", ""), ("CollisionScale", "0.001 0.001 0.001"),
    ):
        group = "Inertial" if property_name in {"InertialXYZ", "InertialRPY", "Mass", "Ixx", "Iyy", "Izz", "Ixy", "Ixz", "Iyz"} else "Geometry"
        link.addProperty("App::PropertyString", property_name, group)
        setattr(link, property_name, value)
    links.addObject(link)


def add_joint(document, joints, name, parent, child, xyz):
    joint = document.addObject("App::FeaturePython", object_name("Joint_", name))
    joint.Label = name
    for property_name, value in (
        ("UrdfName", name), ("JointType", "fixed"), ("Parent", parent), ("Child", child),
        ("OriginXYZ", " ".join(str(value) for value in xyz)), ("OriginRPY", "0 0 0"),
        ("Axis", "0 0 1"), ("Lower", ""), ("Upper", ""), ("Effort", ""), ("Velocity", ""),
    ):
        joint.addProperty("App::PropertyString", property_name, "ROS")
        setattr(joint, property_name, value)
    joint.addProperty("App::PropertyBool", "HasAxis", "ROS")
    joint.HasAxis = False
    joint.addProperty("App::PropertyBool", "HasLimit", "ROS")
    joint.HasLimit = False
    joints.addObject(joint)


document = App.openDocument(str(assembly_path.resolve()))
links = document.getObject("LeKiwiLinks")
joints = document.getObject("LeKiwiJoints")
if not links or not joints:
    raise RuntimeError("missing LeKiwi robot metadata")

for name in ("Link_robotskin_lidar_mount", "Link_ld06_body", "Joint_robotskin_lidar_mount", "Joint_ld06_body", "RobotSkinLidarMount", "LD06Body"):
    remove(document, name)

mount = document.addObject("Mesh::Feature", "RobotSkinLidarMount")
mount.Label = "RobotSkin LeKiwi lidar base"
mount.Mesh = Mesh.Mesh(str(mount_path.resolve()))
mount.addProperty("App::PropertyString", "SourceFile", "Source")
mount.SourceFile = source_path.as_posix()
mount.addProperty("App::PropertyString", "GeneratedMesh", "Source")
mount.GeneratedMesh = mount_path.as_posix()
mount.addProperty("App::PropertyString", "SourceKind", "Source")
mount.SourceKind = "RobotSkin OpenSCAD source"
mount.Visibility = False
add_link(document, links, "robotskin_lidar_mount", mount)
add_joint(document, joints, "robotskin_lidar_mount", "base_plate_layer1-v5", "robotskin_lidar_mount", MOUNT_ORIGIN)

lidar = document.addObject("Part::Feature", "LD06Body")
lidar.Label = "LDROBOT LD06 lidar"
lidar.Shape = Part.makeCylinder(LD06_RADIUS_MM, LD06_HEIGHT_MM)
lidar.addProperty("App::PropertyString", "SourceKind", "Source")
lidar.SourceKind = "LDROBOT LD06 cylindrical envelope"
lidar.Visibility = False
add_link(document, links, "ld06_body", lidar)
add_joint(document, joints, "ld06_body", "robotskin_lidar_mount", "ld06_body", LD06_CENTER)

document.recompute()
document.save()
output = assembly_path.parent.parent.parent / "URDF/meshes/reauthored"
output.mkdir(parents=True, exist_ok=True)
for name in ("robotskin_lidar_mount", "ld06_body"):
    link = next(item for item in links.Group if item.UrdfName == name)
    Mesh.export(link.CadParts, str(output / f"{name}.stl"))
print("added RobotSkin lidar mount and LD06 body")
