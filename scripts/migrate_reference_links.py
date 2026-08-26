"""Create exact link-local FreeCAD reference geometry from STEP and canonical STL files."""

import json
import math
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import FreeCAD as App
import Mesh


ASSEMBLY = Path("cad/assembly/LeKiwi.FCStd")
URDF = Path("URDF/LeKiwi.urdf")
MAPPING = Path("cad/reference_mapping.json")
MODE = os.environ.get("CAD_MIGRATION_MODE") or "report"
MAX_ERROR = 0.02
NATIVE_PARTS = {
    "base_plate_layer1-v5": "CadBasePlateLower",
    "base_plate_layer2-v3": "CadBasePlateUpper",
}
STEP_OBJECTS = {
    "drive_motor_mount-v11-2": "Part__Feature001",
    "ST3215_Servo_Motor-v1-2": "ST3215_Servo_Motor_v1",
    "4-Omni-Directional-Wheel_Single_Body-v1-2": "_4_Omni_Directional_Wheel_Single_Body_v1",
    "omni_wheel_mount-v5-2": "Part__Feature020",
    "drive_motor_mount-v11-1": "Part__Feature021",
    "ST3215_Servo_Motor-v1-1": "ST3215_Servo_Motor_v001",
    "omni_wheel_mount-v5-1": "Part__Feature027",
    "4-Omni-Directional-Wheel_Single_Body-v1-1": "_4_Omni_Directional_Wheel_Single_Body_v001",
    "drive_motor_mount-v11": "Part__Feature041",
    "ST3215_Servo_Motor-v1": "ST3215_Servo_Motor_v002",
    "omni_wheel_mount-v5": "Part__Feature047",
    "4-Omni-Directional-Wheel_Single_Body-v1": "_4_Omni_Directional_Wheel_Single_Body_v002",
    "servo_controller_mount-v3": "Part__Feature061",
    "lipo_battery_mount-v3": "Part__Feature062",
    "Battery---Battery-5.2-Ah-DC5521-Plug-v2": "Part__Feature063",
    "94868A713_NO-THREADS_Female-Threaded-Hex-Standoff": "Part__Feature064",
    "Bottom-V2-v3": "Part__Feature066",
    "Top-V2-v2": "Part__Feature067",
    "Camera-Mount-v8": "Part__Feature068",
    "Camera-Model-v3": "Camera_Model_v3",
    "Base_08q-v1": "Base_08q_v1",
    "WaveShare_Mounting_Plate_01d-v1": "Part__Feature078",
    "Rotation_Pitch_08i-v1": "Part__Feature079",
    "STS3215_03a-v1": "Part__Feature080",
    "SO_ARM100_08k_Asym_Mirror_Clip-v1": "Part__Feature081",
    "Passive_Horn_01-v1": "Part__Feature082",
    "STS3215_03a-v1-1": "Part__Feature083",
    "SO_ARM100_08k_116_Square-v1": "Part__Feature084",
    "STS3215_03a-v1-2": "Part__Feature085",
    "SO_ARM100_08k_Mirror-v1": "SO_ARM100_08k_Mirror_v1",
    "STS3215_03a-v1-3": "Part__Feature088",
    "Wrist_Roll_Pitch_08i-v1": "Part__Feature089",
    "STS3215_03a_Wrist_Roll-v1": "Part__Feature090",
    "Wrist_Roll_08c-v1": "Part__Feature091",
    "STS3215_03a-v1-4": "Part__Feature092",
    "Moving_Jaw_08d-v1": "Part__Feature093",
    "Wrist-Camera-Mount-v11": "Part__Feature094",
    "94868A713_NO-THREADS_Female-Threaded-Hex-Standoff-1": "Part__Feature100",
    "94868A713_NO-THREADS_Female-Threaded-Hex-Standoff-2": "Part__Feature099",
    "Camera-Model-v3-1": "Camera_Model_v001",
    "94868A713_NO-THREADS_Female-Threaded-Hex-Standoff-3": "Part__Feature074",
    "94868A713_NO-THREADS_Female-Threaded-Hex-Standoff-4": "Part__Feature073",
    "94868A713_NO-THREADS_Female-Threaded-Hex-Standoff-5": "Part__Feature072",
}


def numbers(value, scale=1.0):
    return [float(item) * scale for item in value.split()]


def pose(origin):
    x, y, z = numbers(origin.get("xyz", "0 0 0"), 1000.0)
    roll, pitch, yaw = numbers(origin.get("rpy", "0 0 0"))
    cosine, sine = math.cos, math.sin
    return (
        (
            cosine(yaw) * cosine(pitch),
            cosine(yaw) * sine(pitch) * sine(roll) - sine(yaw) * cosine(roll),
            cosine(yaw) * sine(pitch) * cosine(roll) + sine(yaw) * sine(roll),
            x,
        ),
        (
            sine(yaw) * cosine(pitch),
            sine(yaw) * sine(pitch) * sine(roll) + cosine(yaw) * cosine(roll),
            sine(yaw) * sine(pitch) * cosine(roll) - cosine(yaw) * sine(roll),
            y,
        ),
        (-sine(pitch), cosine(pitch) * sine(roll), cosine(pitch) * cosine(roll), z),
        (0.0, 0.0, 0.0, 1.0),
    )


def app_matrix(matrix):
    result = App.Matrix()
    for row in range(4):
        for column in range(4):
            setattr(result, f"A{row + 1}{column + 1}", matrix[row][column])
    return result


def bounds(shape_or_mesh):
    box = shape_or_mesh.BoundBox
    return box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax


def bounds_error(left, right):
    scale = max(right[3] - right[0], right[4] - right[1], right[5] - right[2], 1.0)
    return sum(abs(a - b) for a, b in zip(left, right)) / scale


def bounds_center(values):
    return tuple((values[index] + values[index + 3]) / 2 for index in range(3))


def occurrence_placement(item):
    if item.TypeId == "App::Part":
        children = [
            child.Shape.Placement
            for child in item.Group
            if hasattr(child, "Shape") and not child.Shape.isNull() and child.Shape.Solids
        ]
        if children and all(child.isSame(children[0]) for child in children[1:]):
            return children[0]
    return item.Shape.Placement


def local_shape(item):
    """Remove the STEP assembly occurrence placement without changing BREP geometry."""
    shape = item.Shape.copy()
    placement = occurrence_placement(item)
    shape.Placement = placement.inverse() * shape.Placement
    return shape


def translated_to_bounds(shape, target_bounds):
    source_center = bounds_center(bounds(shape))
    target_center = bounds_center(target_bounds)
    aligned = shape.copy()
    aligned.Placement.Base += App.Vector(*(target_center[index] - source_center[index] for index in range(3)))
    return aligned


def transformed_shape(shape, matrix):
    transformed = shape.copy()
    transformed.Placement = App.Placement(app_matrix(matrix)) * transformed.Placement
    return transformed


def object_name(link_name):
    return "CadReference_" + re.sub(r"[^0-9A-Za-z_]", "_", link_name)


if MODE not in ("report", "apply"):
    raise SystemExit("CAD_MIGRATION_MODE must be report or apply")

root = ET.parse(URDF).getroot()
link_xml = {link.get("name"): link for link in root.findall("link")}
expected = set(link_xml) - set(NATIVE_PARTS)
if set(STEP_OBJECTS) != expected:
    missing = sorted(expected - set(STEP_OBJECTS))
    extra = sorted(set(STEP_OBJECTS) - expected)
    raise RuntimeError(f"STEP mapping mismatch; missing={missing}, extra={extra}")

document = App.openDocument(str(ASSEMBLY.resolve()))
links_group = document.getObject("LeKiwiLinks")
if not links_group:
    raise RuntimeError("missing LeKiwi robot metadata; run seed_robot_metadata.sh first")
metadata = {item.UrdfName: item for item in links_group.Group}

matches = []
for link_name, xml in link_xml.items():
    visual = xml.find("visual")
    mesh_xml = visual.find("geometry/mesh") if visual is not None else None
    if mesh_xml is None:
        raise RuntimeError(f"{link_name}: visual mesh is required")
    mesh_path = URDF.parent / mesh_xml.get("filename")
    mesh = Mesh.Mesh(str(mesh_path))
    origin = visual.find("origin")
    visual_matrix = pose(origin if origin is not None else ET.Element("origin"))
    mesh_bounds = bounds(mesh)
    volume = mesh.Volume
    if link_name in NATIVE_PARTS:
        source = document.getObject(NATIVE_PARTS[link_name])
        if not source or source.Shape.isNull():
            raise RuntimeError(f"{link_name}: missing native source {NATIVE_PARTS[link_name]}")
        output_bounds = bounds(source.Shape)
        target_mesh = Mesh.Mesh(str(mesh_path))
        target_mesh.transform(app_matrix(visual_matrix))
        match = {
            "urdf_link": link_name,
            "reference_object": source.Name,
            "reference_label": source.Label,
            "reference_type": source.TypeId,
            "source_kind": "native FreeCAD laser-cut source",
            "source_bbox_error": bounds_error(output_bounds, bounds(target_mesh)),
            "link_bbox_error": bounds_error(output_bounds, bounds(target_mesh)),
            "volume_error": abs(source.Shape.Volume / volume - 1.0),
            "mesh_filename": mesh_xml.get("filename"),
        }
    else:
        source = document.getObject(STEP_OBJECTS[link_name])
        if not source or source.Shape.isNull() or not source.Shape.Solids:
            raise RuntimeError(f"{link_name}: missing STEP object {STEP_OBJECTS[link_name]}")
        raw_shape = translated_to_bounds(local_shape(source), mesh_bounds)
        source_error = bounds_error(bounds(raw_shape), mesh_bounds)
        output_shape = transformed_shape(raw_shape, visual_matrix)
        target_mesh = Mesh.Mesh(str(mesh_path))
        target_mesh.transform(app_matrix(visual_matrix))
        link_error = bounds_error(bounds(output_shape), bounds(target_mesh))
        volume_error = abs(raw_shape.Volume / volume - 1.0)
        source_kind = "STEP BREP reference" if max(source_error, link_error, volume_error) <= MAX_ERROR else "canonical URDF STL mesh reference"
        if source_kind != "STEP BREP reference":
            link_error = 0.0
        match = {
            "urdf_link": link_name,
            "reference_object": source.Name,
            "reference_label": source.Label,
            "reference_type": source.TypeId,
            "source_kind": source_kind,
            "source_bbox_error": source_error,
            "link_bbox_error": link_error,
            "volume_error": volume_error,
            "mesh_filename": mesh_xml.get("filename"),
        }
    match["visual_xyz"] = origin.get("xyz", "0 0 0") if origin is not None else "0 0 0"
    match["visual_rpy"] = origin.get("rpy", "0 0 0") if origin is not None else "0 0 0"
    matches.append(match)

if MODE == "apply":
    failures = [
        match
        for match in matches
        if match["source_kind"] != "canonical URDF STL mesh reference"
        and (match["link_bbox_error"] > MAX_ERROR or match["volume_error"] > MAX_ERROR)
    ]
    if failures:
        detail = ", ".join(
            f"{match['urdf_link']} (bbox={match['link_bbox_error']:.3%}, volume={match['volume_error']:.3%})"
            for match in failures
        )
        raise RuntimeError(f"invalid link-local reference geometry: {detail}")

    group = document.getObject("LeKiwiReferenceParts")
    existing = set(group.Group) if group else set()
    for link in metadata.values():
        foreign = [part for part in link.CadParts if part not in existing]
        if link.UrdfName not in NATIVE_PARTS and foreign:
            raise RuntimeError(f"{link.UrdfName}: refusing to replace an existing CAD source")
    if not group:
        group = document.addObject("App::DocumentObjectGroup", "LeKiwiReferenceParts")
        group.Label = "Link-local CAD references"
    for part in list(group.Group):
        for link in metadata.values():
            link.CadParts = [item for item in link.CadParts if item != part]
        document.removeObject(part.Name)

    for match in matches:
        if match["urdf_link"] in NATIVE_PARTS:
            continue
        link = metadata[match["urdf_link"]]
        source = document.getObject(match["reference_object"])
        part = document.addObject("Part::Feature" if match["source_kind"] == "STEP BREP reference" else "Mesh::Feature", object_name(link.UrdfName))
        part.Label = f"{match['source_kind']} — {link.UrdfName}"
        part.addProperty("App::PropertyString", "UrdfLink", "Source")
        part.addProperty("App::PropertyString", "ReferenceObject", "Source")
        part.addProperty("App::PropertyString", "SourceKind", "Source")
        part.UrdfLink = link.UrdfName
        part.ReferenceObject = match["reference_object"]
        part.SourceKind = match["source_kind"]
        visual_origin = ET.Element("origin", {"xyz": match["visual_xyz"], "rpy": match["visual_rpy"]})
        if match["source_kind"] == "STEP BREP reference":
            part.Shape = transformed_shape(translated_to_bounds(local_shape(source), bounds(Mesh.Mesh(str(URDF.parent / match["mesh_filename"])))), pose(visual_origin))
        else:
            reference_mesh = Mesh.Mesh(str(URDF.parent / match["mesh_filename"]))
            reference_mesh.transform(app_matrix(pose(visual_origin)))
            part.Mesh = reference_mesh
        part.Visibility = False
        group.addObject(part)
        link.CadParts = [part]
        link.UseCadMass = False

    document.recompute()
    document.save()
    MAPPING.write_text(json.dumps(matches, indent=2) + "\n")
    brep_count = sum(match["source_kind"] == "STEP BREP reference" for match in matches)
    mesh_count = sum(match["source_kind"] == "canonical URDF STL mesh reference" for match in matches)
    print(f"embedded {brep_count} STEP BREP and {mesh_count} canonical mesh references")
else:
    print(json.dumps(matches, indent=2))
