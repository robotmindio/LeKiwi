"""Verify that FreeCAD-exported link meshes preserve the URDF geometry."""

import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import FreeCAD as App
import Mesh


MAX_ERROR = 0.02


def numbers(value, scale=1.0):
    return [float(item) * scale for item in value.split()]


def matrix(origin):
    x, y, z = numbers(origin.get("xyz", "0 0 0"), 1000.0)
    roll, pitch, yaw = numbers(origin.get("rpy", "0 0 0"))
    cosine, sine = math.cos, math.sin
    values = (
        (cosine(yaw) * cosine(pitch), cosine(yaw) * sine(pitch) * sine(roll) - sine(yaw) * cosine(roll), cosine(yaw) * sine(pitch) * cosine(roll) + sine(yaw) * sine(roll), x),
        (sine(yaw) * cosine(pitch), sine(yaw) * sine(pitch) * sine(roll) + cosine(yaw) * cosine(roll), sine(yaw) * sine(pitch) * cosine(roll) - cosine(yaw) * sine(roll), y),
        (-sine(pitch), cosine(pitch) * sine(roll), cosine(pitch) * cosine(roll), z),
        (0.0, 0.0, 0.0, 1.0),
    )
    result = App.Matrix()
    for row in range(4):
        for column in range(4):
            setattr(result, f"A{row + 1}{column + 1}", values[row][column])
    return result


def bounds(mesh):
    box = mesh.BoundBox
    return box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax


def bounds_error(left, right):
    scale = max(right[3] - right[0], right[4] - right[1], right[5] - right[2], 1.0)
    return sum(abs(a - b) for a, b in zip(left, right)) / scale


if len(sys.argv) != 4:
    raise SystemExit("usage: verify_cad_migration.py BASELINE.urdf MAPPING.json REAUTHORED_MESH_DIRECTORY")

urdf_path, mapping_path, output_directory = map(Path, sys.argv[1:])
mapping = {item["urdf_link"]: item for item in json.loads(mapping_path.read_text())}
root = ET.parse(urdf_path).getroot()
links = root.findall("link")
if set(mapping) != {link.get("name") for link in links}:
    raise SystemExit("mapping does not cover exactly the URDF links")

for link in links:
    name = link.get("name")
    visual = link.find("visual")
    mesh_xml = visual.find("geometry/mesh") if visual is not None else None
    if mesh_xml is None:
        raise SystemExit(f"{name}: visual mesh is required")
    expected = Mesh.Mesh(str(urdf_path.parent / mesh_xml.get("filename")))
    origin = visual.find("origin")
    expected.transform(matrix(origin if origin is not None else ET.Element("origin")))
    actual_path = output_directory / (re.sub(r"[^0-9A-Za-z_.-]", "_", name) + ".stl")
    if not actual_path.is_file() or actual_path.stat().st_size == 0:
        raise SystemExit(f"{name}: missing exported mesh {actual_path}")
    actual = Mesh.Mesh(str(actual_path))
    box_error = bounds_error(bounds(actual), bounds(expected))
    volume_error = abs(abs(actual.Volume) / abs(expected.Volume) - 1.0)
    tolerance = 1e-6 if mapping[name]["source_kind"] == "canonical URDF STL mesh reference" else MAX_ERROR
    if box_error > tolerance or volume_error > tolerance:
        raise SystemExit(f"{name}: mesh mismatch (bbox={box_error:.3%}, volume={volume_error:.3%})")

print(f"validated {len(links)} CAD-derived meshes against the baseline URDF")
