"""Verify that FreeCAD-exported link meshes preserve the URDF geometry."""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import Mesh

from scripts.cad_utils import bounds, bounds_error, mesh_filename, urdf_matrix

MAX_ERROR = 0.02


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
    expected.transform(urdf_matrix(origin if origin is not None else ET.Element("origin")))
    actual_path = output_directory / mesh_filename(name)
    if not actual_path.is_file() or actual_path.stat().st_size == 0:
        raise SystemExit(f"{name}: missing exported mesh {actual_path}")
    actual = Mesh.Mesh(str(actual_path))
    box_error = bounds_error(bounds(actual), bounds(expected))
    volume_error = abs(abs(actual.Volume) / abs(expected.Volume) - 1.0)
    tolerance = 1e-6 if mapping[name]["source_kind"] == "canonical URDF STL mesh reference" else MAX_ERROR
    if box_error > tolerance or volume_error > tolerance:
        raise SystemExit(f"{name}: mesh mismatch (bbox={box_error:.3%}, volume={volume_error:.3%})")

print(f"validated {len(links)} CAD-derived meshes against the baseline URDF")
