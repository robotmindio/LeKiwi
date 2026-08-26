"""Verify the locally imported FreeCAD accessory sources against their original STLs."""

from pathlib import Path

import FreeCAD as App
import Mesh


ACCESSORIES = (
    ("webcam_base_mount", Path("3DPrintMeshes/webcam_mount/webcam_mount.stl")),
    ("webcam_wrist_mount", Path("3DPrintMeshes/webcam_mount/webcam_mount_wrist.stl")),
)
MAX_ERROR = 0.02


def bounds(shape_or_mesh):
    box = shape_or_mesh.BoundBox
    return box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax


def bounds_error(left, right):
    scale = max(right[3] - right[0], right[4] - right[1], right[5] - right[2], 1.0)
    return sum(abs(a - b) for a, b in zip(left, right)) / scale


for name, mesh_path in ACCESSORIES:
    source_path = Path("cad/accessories") / f"{name}.FCStd"
    if not source_path.is_file() or not mesh_path.is_file():
        raise RuntimeError(f"{name}: missing source document or original STL")
    document = App.openDocument(str(source_path.resolve()))
    final = document.getObject("Final")
    if not final or final.Shape.isNull() or not final.Shape.Solids:
        raise RuntimeError(f"{name}: missing imported STEP solid")
    if getattr(final, "SourceKind", "") != "Published LeKiwi STEP BREP source":
        raise RuntimeError(f"{name}: source provenance is missing")
    expected = Mesh.Mesh(str(mesh_path))
    box_error = bounds_error(bounds(final.Shape), bounds(expected))
    volume_error = abs(final.Shape.Volume / abs(expected.Volume) - 1.0)
    App.closeDocument(document.Name)
    if box_error > MAX_ERROR or volume_error > MAX_ERROR:
        raise RuntimeError(f"{name}: STEP/STL mismatch (bbox={box_error:.3%}, volume={volume_error:.3%})")
    print(f"validated {name}: bbox={box_error:.3%}, volume={volume_error:.3%}")
