"""Generate Xacro from LeKiwi FreeCAD robot metadata."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import FreeCAD as App

from scripts.cad_utils import mesh_filename


XACRO_NS = "http://www.ros.org/wiki/xacro"
ET.register_namespace("xacro", XACRO_NS)


def add(parent, tag, **attrs):
    return ET.SubElement(
        parent, tag, {key: value for key, value in attrs.items() if value != ""}
    )


def property_value(obj, name):
    return str(getattr(obj, name))


def mesh_path(path):
    prefix = "meshes/"
    return "${mesh_dir}/" + (path[len(prefix) :] if path.startswith(prefix) else path)


def geometry_mesh(link, kind):
    return (
        "meshes/reauthored/" + mesh_filename(link.UrdfName)
        if link.CadParts
        else property_value(link, kind + "Mesh")
    )


def matrix_values(matrix):
    return (
        (matrix.A11, matrix.A12, matrix.A13),
        (matrix.A12, matrix.A22, matrix.A23),
        (matrix.A13, matrix.A23, matrix.A33),
    )


def cad_inertial(link):
    parts = link.CadParts
    if not parts:
        raise RuntimeError(f"{link.UrdfName}: UseCadMass needs one or more CadParts")

    entries = []
    for part in parts:
        if not hasattr(part, "Shape") or part.Shape.isNull() or not part.Shape.Solids:
            raise RuntimeError(f"{link.UrdfName}: {part.Label} is not a solid CAD part")
        if not hasattr(part, "MassOverride") or not hasattr(part, "MaterialDensity"):
            raise RuntimeError(
                f"{link.UrdfName}: {part.Label} needs MassOverride and MaterialDensity properties"
            )
        solids = part.Shape.Solids
        volume = sum(shape.Volume for shape in solids)  # mm^3
        mass_override = float(part.MassOverride)
        density = float(part.MaterialDensity) / 1_000_000_000  # kg/mm^3
        total_mass = mass_override if mass_override > 0 else volume * density
        if total_mass <= 0:
            raise RuntimeError(f"{link.UrdfName}: {part.Label} has no usable mass")
        for shape in solids:
            mass = total_mass * shape.Volume / volume
            scale = mass / shape.Volume  # scales volume inertia from mm^5 to kg*mm^2
            center = shape.CenterOfMass * 0.001  # m
            inertia = tuple(
                tuple(value * scale * 1e-6 for value in row)
                for row in matrix_values(shape.MatrixOfInertia)
            )
            entries.append((mass, center, inertia))

    mass = sum(entry[0] for entry in entries)
    center = sum((entry[1] * entry[0] for entry in entries), App.Vector()) / mass
    inertia = [[0.0] * 3 for _ in range(3)]
    for part_mass, part_center, part_inertia in entries:
        offset = part_center - center
        distance_squared = offset.dot(offset)
        vector = (offset.x, offset.y, offset.z)
        for row in range(3):
            for column in range(3):
                inertia[row][column] += part_inertia[row][column] + part_mass * (
                    (distance_squared if row == column else 0.0)
                    - vector[row] * vector[column]
                )
    return {
        "xyz": f"{center.x:.17g} {center.y:.17g} {center.z:.17g}",
        "rpy": "0 0 0",
        "mass": f"{mass:.17g}",
        "ixx": f"{inertia[0][0]:.17g}",
        "iyy": f"{inertia[1][1]:.17g}",
        "izz": f"{inertia[2][2]:.17g}",
        "ixy": f"{inertia[0][1]:.17g}",
        "ixz": f"{inertia[0][2]:.17g}",
        "iyz": f"{inertia[1][2]:.17g}",
    }


def fallback_inertial(link):
    return {
        "xyz": property_value(link, "InertialXYZ"),
        "rpy": property_value(link, "InertialRPY"),
        "mass": property_value(link, "Mass"),
        "ixx": property_value(link, "Ixx"),
        "iyy": property_value(link, "Iyy"),
        "izz": property_value(link, "Izz"),
        "ixy": property_value(link, "Ixy"),
        "ixz": property_value(link, "Ixz"),
        "iyz": property_value(link, "Iyz"),
    }


if len(sys.argv) != 3:
    raise SystemExit("usage: export_xacro.py INPUT.FCStd OUTPUT.urdf.xacro")

source, output = map(Path, sys.argv[1:])
document = App.openDocument(str(source))
links_group = document.getObject("LeKiwiLinks")
joints_group = document.getObject("LeKiwiJoints")
if not links_group or not joints_group:
    raise RuntimeError(
        "missing LeKiwi robot metadata; run seed_robot_metadata.sh first"
    )

root = ET.Element("robot", {"name": "LeKiwi"})
ET.SubElement(root, f"{{{XACRO_NS}}}property", {"name": "mesh_dir", "value": "meshes"})
for link in links_group.Group:
    node = add(root, "link", name=property_value(link, "UrdfName"))
    inertial = cad_inertial(link) if link.UseCadMass else fallback_inertial(link)
    if float(inertial["mass"]) > 0:
        inertial_node = add(node, "inertial")
        add(inertial_node, "origin", xyz=inertial["xyz"], rpy=inertial["rpy"])
        add(inertial_node, "mass", value=inertial["mass"])
        add(
            inertial_node,
            "inertia",
            **{
                key: inertial[key] for key in ("ixx", "iyy", "izz", "ixy", "ixz", "iyz")
            },
        )
    for kind in ("Visual", "Collision"):
        element = add(node, kind.lower(), name=property_value(link, kind + "Name"))
        origin = (
            ("0 0 0", "0 0 0")
            if link.CadParts
            else (
                property_value(link, kind + "XYZ"),
                property_value(link, kind + "RPY"),
            )
        )
        add(element, "origin", xyz=origin[0], rpy=origin[1])
        geometry = add(element, "geometry")
        add(
            geometry,
            "mesh",
            filename=mesh_path(geometry_mesh(link, kind)),
            scale=property_value(link, kind + "Scale"),
        )

for joint in joints_group.Group:
    node = add(
        root,
        "joint",
        name=property_value(joint, "UrdfName"),
        type=property_value(joint, "JointType"),
    )
    add(
        node,
        "origin",
        xyz=property_value(joint, "OriginXYZ"),
        rpy=property_value(joint, "OriginRPY"),
    )
    add(node, "parent", link=property_value(joint, "Parent"))
    add(node, "child", link=property_value(joint, "Child"))
    if joint.HasAxis:
        add(node, "axis", xyz=property_value(joint, "Axis"))
    if joint.HasLimit:
        add(
            node,
            "limit",
            lower=property_value(joint, "Lower"),
            upper=property_value(joint, "Upper"),
            effort=property_value(joint, "Effort"),
            velocity=property_value(joint, "Velocity"),
        )

ET.indent(root, space="    ")
output.parent.mkdir(parents=True, exist_ok=True)
ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
print(
    f"saved {output} with {len(links_group.Group)} links and {len(joints_group.Group)} joints"
)
