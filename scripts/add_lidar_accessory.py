"""Add the deterministic sensor mounts and RPi 5 stack to the editable LeKiwi assembly."""

import hashlib
import sys
import json
from pathlib import Path

import FreeCAD as App
import Mesh
import Part

from scripts.cad_utils import PI_CASE_LINKS, object_name


if len(sys.argv) != 12:
    raise SystemExit(
        "usage: add_lidar_accessory.py ASSEMBLY.FCStd LIDAR.scad LIDAR.stl ASTRA.scad ASTRA.stl"
        " RPI5_PLATE.scad RPI5_PLATE.stl RPI5_CARRIER.scad RPI5_CARRIER.stl"
        " RPI5_TABLE.scad RPI5_TABLE.stl"
    )


assembly_path, lidar_source, lidar_mesh, astra_source, astra_mesh = map(Path, sys.argv[1:6])
rpi5_parts = (
    ("rpi5_through_plate", "RPi5ThroughPlate", "RobotSkin 12x10 through plate", *sys.argv[6:8]),
    ("rpi5_usb_carrier", "RPi5UsbCarrier", "RobotSkin RPi 5 + USB board carrier", *sys.argv[8:10]),
    ("rpi5_table", "RPi5Table", "RobotSkin RPi 5 protection table", *sys.argv[10:12]),
)
spec = json.loads(Path("cad/accessories/sensor_mount_spec.json").read_text())
for source, mesh, name in (
    (lidar_source, lidar_mesh, "RobotSkin lidar"),
    (astra_source, astra_mesh, "Astra compact mount"),
    *((Path(source), Path(mesh), label) for _, _, label, source, mesh in rpi5_parts),
):
    if not source.is_file():
        raise RuntimeError(f"missing {name} OpenSCAD source: {source}")
    if not mesh.is_file():
        raise RuntimeError(f"missing generated {name} mesh: {mesh}")

MOUNT_ORIGIN = tuple(spec["lidar"]["mount_origin_m"])
MOUNT_RPY = tuple(spec["lidar"]["mount_rpy_rad"])
LD06_CENTER = tuple(spec["lidar"]["body_center_m"])
LD06_RADIUS_MM = spec["lidar"]["body_radius_mm"]
LD06_HEIGHT_MM = spec["lidar"]["body_height_mm"]
ASTRA_MOUNT_ORIGIN = tuple(spec["astra"]["mount_origin_m"])
ASTRA_MOUNT_RPY = tuple(spec["astra"]["mount_rpy_rad"])
RPI5 = spec["rpi5"]


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def joint_matches(document, name, parent, child, xyz, rpy=(0, 0, 0)):
    joint = document.getObject(object_name("Joint_", name))
    if not joint:
        return False
    expected_xyz = " ".join(str(value) for value in xyz)
    expected_rpy = " ".join(str(value) for value in rpy)
    return (
        joint.Parent == parent
        and joint.Child == child
        and joint.OriginXYZ == expected_xyz
        and joint.OriginRPY == expected_rpy
    )


def mesh_source_matches(document, name, source):
    # Compare the OpenSCAD *source* hash, not the regenerated STL's: OpenSCAD's
    # STL export is not byte-stable across identical runs (facet order and
    # float formatting vary), so hashing the mesh would never match twice in
    # a row even when nothing changed.
    link = document.getObject(object_name("Link_", name))
    if not link or not link.CadParts:
        return False
    part = link.CadParts[0]
    return (
        hasattr(part, "SourceFile")
        and hasattr(part, "SourceHash")
        and part.SourceFile == source.as_posix()
        and part.SourceHash == file_hash(source)
    )


def cylinder_source_matches(document, name, radius, height):
    link = document.getObject(object_name("Link_", name))
    if not link or not link.CadParts:
        return False
    part = link.CadParts[0]
    return (
        hasattr(part, "SourceRadiusMm")
        and hasattr(part, "SourceHeightMm")
        and abs(part.SourceRadiusMm - radius) < 1e-9
        and abs(part.SourceHeightMm - height) < 1e-9
    )


def mounts_already_current(document, links_group):
    """True when every sensor mount already matches its current source.

    Every export runs this script, so without a change check it would remove
    and re-add each mount and save the assembly on every export even when the
    OpenSCAD sources, meshes, and mount spec are unchanged, churning the
    binary FCStd for no reason.
    """
    existing_links = {item.UrdfName for item in links_group.Group}
    if PI_CASE_LINKS & existing_links:
        return False
    return (
        mesh_source_matches(document, "robotskin_lidar_mount", lidar_source)
        and joint_matches(
            document,
            "robotskin_lidar_mount_joint",
            "base_plate_layer2-v3",
            "robotskin_lidar_mount",
            MOUNT_ORIGIN,
            MOUNT_RPY,
        )
        and cylinder_source_matches(document, "ld06_body", LD06_RADIUS_MM, LD06_HEIGHT_MM)
        and joint_matches(
            document,
            "ld06_body_mount",
            "robotskin_lidar_mount",
            "ld06_body",
            LD06_CENTER,
        )
        and mesh_source_matches(document, "astra_pro_compact_mount", astra_source)
        and joint_matches(
            document,
            "astra_pro_compact_mount_joint",
            "base_plate_layer2-v3",
            "astra_pro_compact_mount",
            ASTRA_MOUNT_ORIGIN,
            ASTRA_MOUNT_RPY,
        )
    )


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
        ("InertialXYZ", "0 0 0"),
        ("InertialRPY", "0 0 0"),
        ("Mass", "0"),
        ("Ixx", "0"),
        ("Iyy", "0"),
        ("Izz", "0"),
        ("Ixy", "0"),
        ("Ixz", "0"),
        ("Iyz", "0"),
        ("VisualName", name + "_visual"),
        ("VisualXYZ", "0 0 0"),
        ("VisualRPY", "0 0 0"),
        ("VisualMesh", ""),
        ("VisualScale", "0.001 0.001 0.001"),
        ("CollisionName", name + "_collision"),
        ("CollisionXYZ", "0 0 0"),
        ("CollisionRPY", "0 0 0"),
        ("CollisionMesh", ""),
        ("CollisionScale", "0.001 0.001 0.001"),
    ):
        group = (
            "Inertial"
            if property_name
            in {
                "InertialXYZ",
                "InertialRPY",
                "Mass",
                "Ixx",
                "Iyy",
                "Izz",
                "Ixy",
                "Ixz",
                "Iyz",
            }
            else "Geometry"
        )
        link.addProperty("App::PropertyString", property_name, group)
        setattr(link, property_name, value)
    links.addObject(link)


def add_joint(document, joints, name, parent, child, xyz, rpy=(0, 0, 0)):
    joint = document.addObject("App::FeaturePython", object_name("Joint_", name))
    joint.Label = name
    for property_name, value in (
        ("UrdfName", name),
        ("JointType", "fixed"),
        ("Parent", parent),
        ("Child", child),
        ("OriginXYZ", " ".join(str(value) for value in xyz)),
        ("OriginRPY", " ".join(str(value) for value in rpy)),
        ("Axis", "0 0 1"),
        ("Lower", ""),
        ("Upper", ""),
        ("Effort", ""),
        ("Velocity", ""),
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

if mounts_already_current(document, links):
    output = assembly_path.parent.parent.parent / "URDF/meshes/reauthored"
    output.mkdir(parents=True, exist_ok=True)
    for name in ("robotskin_lidar_mount", "ld06_body", "astra_pro_compact_mount"):
        link = next(item for item in links.Group if item.UrdfName == name)
        Mesh.export(link.CadParts, str(output / f"{name}.stl"))
    print("sensor mounts already match their sources; no assembly changes")
    sys.exit(0)

# Keep the historical reference parts, but do not export the removed Pi case
# as installed hardware. Their old mounting datum remains in the source URDF.
for joint in list(joints.Group):
    if joint.Child in PI_CASE_LINKS:
        document.removeObject(joint.Name)
for link in list(links.Group):
    if link.UrdfName in PI_CASE_LINKS:
        for part in link.CadParts:
            part.Visibility = False
        document.removeObject(link.Name)

for name in (
    "Link_robotskin_lidar_mount",
    "Link_ld06_body",
    "Joint_robotskin_lidar_mount",
    "Joint_robotskin_lidar_mount_joint",
    "Joint_ld06_body",
    "Joint_ld06_body_mount",
    "Link_astra_pro_compact_mount",
    "Joint_astra_pro_compact_mount",
    "Joint_astra_pro_compact_mount_joint",
    "RobotSkinLidarMount",
    "LD06Body",
    "AstraProCompactMount",
    *(f"{prefix}_{urdf}{suffix}" for urdf, *_ in rpi5_parts
      for prefix, suffix in (("Link", ""), ("Joint", "_joint"))),
    *(obj for _, obj, *_ in rpi5_parts),
):
    remove(document, name)

mount = document.addObject("Mesh::Feature", "RobotSkinLidarMount")
mount.Label = "RobotSkin LeKiwi lidar base"
mount.Mesh = Mesh.Mesh(str(lidar_mesh.resolve()))
mount.addProperty("App::PropertyString", "SourceFile", "Source")
mount.SourceFile = lidar_source.as_posix()
mount.addProperty("App::PropertyString", "GeneratedMesh", "Source")
mount.GeneratedMesh = lidar_mesh.as_posix()
mount.addProperty("App::PropertyString", "SourceHash", "Source")
mount.SourceHash = file_hash(lidar_source)
mount.addProperty("App::PropertyString", "SourceKind", "Source")
mount.SourceKind = "RobotSkin OpenSCAD source"
mount.Visibility = False
add_link(document, links, "robotskin_lidar_mount", mount)
add_joint(
    document,
    joints,
    "robotskin_lidar_mount_joint",
    "base_plate_layer2-v3",
    "robotskin_lidar_mount",
    MOUNT_ORIGIN,
    MOUNT_RPY,
)

lidar = document.addObject("Part::Feature", "LD06Body")
lidar.Label = "LDROBOT LD06 lidar"
lidar.Shape = Part.makeCylinder(LD06_RADIUS_MM, LD06_HEIGHT_MM)
lidar.addProperty("App::PropertyFloat", "SourceRadiusMm", "Source")
lidar.SourceRadiusMm = LD06_RADIUS_MM
lidar.addProperty("App::PropertyFloat", "SourceHeightMm", "Source")
lidar.SourceHeightMm = LD06_HEIGHT_MM
lidar.addProperty("App::PropertyString", "SourceKind", "Source")
lidar.SourceKind = "LDROBOT LD06 cylindrical envelope"
lidar.Visibility = False
add_link(document, links, "ld06_body", lidar)
add_joint(
    document,
    joints,
    "ld06_body_mount",
    "robotskin_lidar_mount",
    "ld06_body",
    LD06_CENTER,
)

astra = document.addObject("Mesh::Feature", "AstraProCompactMount")
astra.Label = "Astra Pro compact mount"
astra.Mesh = Mesh.Mesh(str(astra_mesh.resolve()))
astra.addProperty("App::PropertyString", "SourceFile", "Source")
astra.SourceFile = astra_source.as_posix()
astra.addProperty("App::PropertyString", "GeneratedMesh", "Source")
astra.GeneratedMesh = astra_mesh.as_posix()
astra.addProperty("App::PropertyString", "SourceHash", "Source")
astra.SourceHash = file_hash(astra_source)
astra.addProperty("App::PropertyString", "SourceKind", "Source")
astra.SourceKind = "Astra Pro compact-mount OpenSCAD source"
astra.Visibility = False
add_link(document, links, "astra_pro_compact_mount", astra)
add_joint(
    document,
    joints,
    "astra_pro_compact_mount_joint",
    "base_plate_layer2-v3",
    "astra_pro_compact_mount",
    ASTRA_MOUNT_ORIGIN,
    ASTRA_MOUNT_RPY,
)

# Plate on the upper chassis plate; carrier and table lock into its ports.
for (urdf, obj, label, source, mesh), parent, xyz, rpy in zip(
    rpi5_parts,
    ("base_plate_layer2-v3", "rpi5_through_plate", "rpi5_through_plate"),
    (RPI5["plate_origin_m"], RPI5["carrier_origin_m"], RPI5["table_origin_m"]),
    (RPI5["plate_rpy_rad"], (0, 0, 0), (0, 0, 0)),
):
    part = document.addObject("Mesh::Feature", obj)
    part.Label = label
    part.Mesh = Mesh.Mesh(str(Path(mesh).resolve()))
    part.addProperty("App::PropertyString", "SourceFile", "Source")
    part.SourceFile = Path(source).as_posix()
    part.addProperty("App::PropertyString", "GeneratedMesh", "Source")
    part.GeneratedMesh = Path(mesh).as_posix()
    part.addProperty("App::PropertyString", "SourceKind", "Source")
    part.SourceKind = "RobotSkin OpenSCAD source"
    part.Visibility = False
    add_link(document, links, urdf, part)
    add_joint(document, joints, urdf + "_joint", parent, urdf, tuple(xyz), tuple(rpy))

document.recompute()
document.save()
output = assembly_path.parent.parent.parent / "URDF/meshes/reauthored"
output.mkdir(parents=True, exist_ok=True)
for name in (
    "robotskin_lidar_mount",
    "ld06_body",
    "astra_pro_compact_mount",
    *(urdf for urdf, *_ in rpi5_parts),
):
    link = next(item for item in links.Group if item.UrdfName == name)
    Mesh.export(link.CadParts, str(output / f"{name}.stl"))
print("added RobotSkin lidar mount, LD06 body, Astra compact mount, and RPi 5 stack")
