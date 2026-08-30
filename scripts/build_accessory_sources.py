"""Build FreeCAD documents for LeKiwi accessories that have published STEP sources."""

from pathlib import Path

import FreeCAD as App
import Import
import Mesh
import Part


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
DERIVATIVE_MAX_BBOX_ERROR = 0.025


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


# The webcam gripper print is the upstream wrist roll with its M3 clearance
# and captive-nut pocket added at the camera interface.
name = "so100_gripper_cam_mount_insert"
step_path = Path("cad/upstream/SO-ARM100/STEP/SO100/Follower_Specific/Wrist_Roll_08c v1.step")
mesh_path = Path("3DPrintMeshes/webcam_mount/so100_gripper_cam_mount_insert.stl")
if not step_path.is_file() or not mesh_path.is_file():
    raise RuntimeError(f"{name}: missing SO-ARM100 source or original STL")
document = App.newDocument(f"LeKiwiAccessory_{name}")
Import.insert(str(step_path.resolve()), document.Name)
imported = [item for item in document.Objects if hasattr(item, "Shape") and not item.Shape.isNull()]
if len(imported) != 1 or not imported[0].Shape.Solids:
    raise RuntimeError(f"{name}: upstream STEP import must contain exactly one solid feature")
source = imported[0]
source.Label = "Upstream SO-100 Wrist Roll"
clearance = document.addObject("Part::Cylinder", "CameraMountM3Clearance")
clearance.Label = "M3 camera-mount clearance"
clearance.Radius = 1.6
clearance.Height = 50
clearance.Placement = App.Placement(App.Vector(-5, 10, 23.4), App.Rotation(App.Vector(1, 0, 0), 90))
nut_trap = document.addObject("Part::Prism", "CameraMountNutTrap")
nut_trap.Label = "M3 hex-nut pocket"
nut_trap.Polygon = 6
nut_trap.Circumradius = 3.2331615
nut_trap.Height = 3.3
nut_trap.Placement = App.Placement(
    App.Vector(-5, -17.2, 23.4),
    App.Rotation(App.Vector(0, 1, 0), 90).multiply(App.Rotation(App.Vector(1, 0, 0), 90)),
)
tools = document.addObject("Part::MultiFuse", "CameraMountCutTools")
tools.Label = "Camera-mount cut tools"
tools.Shapes = [clearance, nut_trap]
tools.Refine = True
final = document.addObject("Part::Cut", "Final")
final.Label = "SO-100 wrist roll with camera-mount clearance"
final.Base = source
final.Tool = tools
final.Refine = True
final.addProperty("App::PropertyString", "SourceFile", "Source")
final.addProperty("App::PropertyString", "OriginalMesh", "Source")
final.addProperty("App::PropertyString", "SourceKind", "Source")
final.SourceFile = step_path.as_posix()
final.OriginalMesh = mesh_path.as_posix()
final.SourceKind = "SO-ARM100 STEP derivative with parametric camera-mount cuts"
metadata = document.addObject("App::FeaturePython", "SourceMetadata")
metadata.Label = "Source provenance"
metadata.addProperty("App::PropertyString", "SourceFile", "Source")
metadata.addProperty("App::PropertyString", "OriginalMesh", "Source")
metadata.addProperty("App::PropertyString", "SourceKind", "Source")
metadata.SourceFile = final.SourceFile
metadata.OriginalMesh = final.OriginalMesh
metadata.SourceKind = final.SourceKind
document.recompute()
expected = Mesh.Mesh(str(mesh_path))
box_error = bounds_error(bounds(final.Shape), bounds(expected))
volume_error = abs(final.Shape.Volume / abs(expected.Volume) - 1.0)
if box_error > DERIVATIVE_MAX_BBOX_ERROR or volume_error > MAX_ERROR:
    raise RuntimeError(f"{name}: source/STL mismatch (bbox={box_error:.3%}, volume={volume_error:.3%})")
output = OUTPUT_DIRECTORY / f"{name}.FCStd"
document.saveAs(str(output.resolve()))
App.closeDocument(document.Name)
print(f"saved {output}: bbox={box_error:.3%}, volume={volume_error:.3%}")
