"""Export link-local FreeCAD solids or meshes to the paths used by Xacro."""

import re
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import MeshPart


LINEAR_DEFLECTION_MM = 0.1
ANGULAR_DEFLECTION_RAD = 0.5


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
    if any(
        (not hasattr(part, "Shape") or part.Shape.isNull())
        and (not hasattr(part, "Mesh") or part.Mesh.CountFacets == 0)
        for part in link.CadParts
    ):
        raise RuntimeError(f"{link.UrdfName}: CadParts must contain FreeCAD shapes or meshes")
    mesh_directory.mkdir(parents=True, exist_ok=True)
    temporary = []
    mesh_parts = []
    for index, part in enumerate(link.CadParts):
        if hasattr(part, "Shape") and not part.Shape.isNull():
            mesh_part = document.addObject("Mesh::Feature", f"ExportMesh_{written}_{index}")
            mesh_part.Mesh = MeshPart.meshFromShape(
                Shape=part.Shape,
                LinearDeflection=LINEAR_DEFLECTION_MM,
                AngularDeflection=ANGULAR_DEFLECTION_RAD,
                Relative=False,
            )
            temporary.append(mesh_part)
            mesh_parts.append(mesh_part)
        else:
            mesh_parts.append(part)
    Mesh.export(mesh_parts, str(mesh_directory / filename(link)))
    for part in temporary:
        document.removeObject(part.Name)
    written += 1
print(f"exported {written} reauthored mesh files to {mesh_directory}")
