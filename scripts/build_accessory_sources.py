"""Build FreeCAD documents for LeKiwi accessories that have published STEP sources."""

from pathlib import Path

import FreeCAD as App
import Import
import Mesh


ACCESSORIES = (
    (
        "webcam_base_mount",
        "Webcam base mount",
        Path("3DPrintMeshes/webcam_mount/webcam_mount.step"),
        Path("3DPrintMeshes/webcam_mount/webcam_mount.stl"),
    ),
    (
        "webcam_wrist_mount",
        "Webcam wrist mount",
        Path("3DPrintMeshes/webcam_mount/webcam_mount_wrist.step"),
        Path("3DPrintMeshes/webcam_mount/webcam_mount_wrist.stl"),
    ),
)
OUTPUT_DIRECTORY = Path("cad/accessories")
MAX_ERROR = 0.02


def bounds(shape_or_mesh):
    box = shape_or_mesh.BoundBox
    return box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax


def bounds_error(left, right):
    scale = max(right[3] - right[0], right[4] - right[1], right[5] - right[2], 1.0)
    return sum(abs(a - b) for a, b in zip(left, right)) / scale


for name, title, step_path, mesh_path in ACCESSORIES:
    if not step_path.is_file() or not mesh_path.is_file():
        raise RuntimeError(f"{name}: missing published STEP source or matching STL")
    document = App.newDocument(f"LeKiwiAccessory_{name}")
    Import.insert(str(step_path.resolve()), document.Name)
    imported = [item for item in document.Objects if hasattr(item, "Shape") and not item.Shape.isNull()]
    if len(imported) != 1 or not imported[0].Shape.Solids:
        raise RuntimeError(f"{name}: STEP import must contain exactly one solid feature")
    final = document.addObject("Part::Feature", "Final")
    final.Label = f"Imported STEP — {title}"
    final.Shape = imported[0].Shape.copy()
    final.addProperty("App::PropertyString", "SourceFile", "Source")
    final.addProperty("App::PropertyString", "OriginalMesh", "Source")
    final.addProperty("App::PropertyString", "SourceKind", "Source")
    final.SourceFile = step_path.as_posix()
    final.OriginalMesh = mesh_path.as_posix()
    final.SourceKind = "Published LeKiwi STEP BREP source"
    metadata = document.addObject("App::FeaturePython", "SourceMetadata")
    metadata.Label = "Source provenance"
    metadata.addProperty("App::PropertyString", "SourceFile", "Source")
    metadata.addProperty("App::PropertyString", "OriginalMesh", "Source")
    metadata.addProperty("App::PropertyString", "SourceKind", "Source")
    metadata.SourceFile = final.SourceFile
    metadata.OriginalMesh = final.OriginalMesh
    metadata.SourceKind = final.SourceKind
    for item in imported:
        document.removeObject(item.Name)
    document.recompute()
    expected = Mesh.Mesh(str(mesh_path))
    box_error = bounds_error(bounds(final.Shape), bounds(expected))
    volume_error = abs(final.Shape.Volume / abs(expected.Volume) - 1.0)
    if box_error > MAX_ERROR or volume_error > MAX_ERROR:
        raise RuntimeError(f"{name}: STEP/STL mismatch (bbox={box_error:.3%}, volume={volume_error:.3%})")
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIRECTORY / f"{name}.FCStd"
    document.saveAs(str(output.resolve()))
    App.closeDocument(document.Name)
    print(f"saved {output}: bbox={box_error:.3%}, volume={volume_error:.3%}")
