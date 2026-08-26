"""Export reauthored FreeCAD link solids to the mesh paths used by Xacro."""

import re
import sys
from pathlib import Path

import FreeCAD as App
import Mesh


def filename(link):
    return re.sub(r"[^0-9A-Za-z_.-]", "_", link.UrdfName) + ".stl"


if len(sys.argv) != 3:
    raise SystemExit("usage: export_cad_meshes.py INPUT.FCStd OUTPUT_MESH_DIRECTORY")

source, mesh_directory = map(Path, sys.argv[1:])
document = App.openDocument(str(source))
links = document.getObject("LeKiwiLinks")
if not links:
    raise RuntimeError("missing LeKiwi robot metadata; run seed_robot_metadata.sh first")

written = 0
for link in links.Group:
    if not link.CadParts:
        continue
    if any(not hasattr(part, "Shape") or part.Shape.isNull() for part in link.CadParts):
        raise RuntimeError(f"{link.UrdfName}: CadParts must contain FreeCAD shapes")
    mesh_directory.mkdir(parents=True, exist_ok=True)
    Mesh.export(link.CadParts, str(mesh_directory / filename(link)))
    written += 1
print(f"exported {written} reauthored mesh files to {mesh_directory}")
