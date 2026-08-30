"""Verify the locally imported FreeCAD accessory sources against their original STLs."""

from pathlib import Path

import FreeCAD as App
import Mesh


ACCESSORIES = (
    ("webcam_base_mount", Path("3DPrintMeshes/webcam_mount/webcam_mount.stl"), "Published LeKiwi STEP BREP source", 0.02),
    ("webcam_wrist_mount", Path("3DPrintMeshes/webcam_mount/webcam_mount_wrist.stl"), "Published LeKiwi STEP BREP source", 0.02),
    (
        "so100_gripper_cam_mount_insert",
        Path("3DPrintMeshes/webcam_mount/so100_gripper_cam_mount_insert.stl"),
        "SO-ARM100 STEP derivative source",
        0.025,
    ),
)
MAX_ERROR = 0.02


def bounds(shape_or_mesh):
    box = shape_or_mesh.BoundBox
    return box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax


def bounds_error(left, right):
    scale = max(right[3] - right[0], right[4] - right[1], right[5] - right[2], 1.0)
    return sum(abs(a - b) for a, b in zip(left, right)) / scale


for name, mesh_path, source_kind, max_bbox_error in ACCESSORIES:
    source_path = Path("cad/accessories") / f"{name}.FCStd"
    if not source_path.is_file() or not mesh_path.is_file():
        raise RuntimeError(f"{name}: missing source document or original STL")
    document = App.openDocument(str(source_path.resolve()))
    final = document.getObject("Final")
    if not final or final.Shape.isNull() or not final.Shape.Solids:
        raise RuntimeError(f"{name}: missing imported STEP solid")
    if getattr(final, "SourceKind", "") != source_kind:
        raise RuntimeError(f"{name}: source provenance is missing")
    if name == "so100_gripper_cam_mount_insert":
        boss = document.getObject("CameraMountBoss")
        if not boss or abs(boss.Radius.Value - 2.4) > 1e-9 or abs(boss.Height.Value - 3.3) > 1e-9:
            raise RuntimeError(f"{name}: missing editable M3 camera-mount boss")
    expected = Mesh.Mesh(str(mesh_path))
    box_error = bounds_error(bounds(final.Shape), bounds(expected))
    volume_error = abs(final.Shape.Volume / abs(expected.Volume) - 1.0)
    App.closeDocument(document.Name)
    if box_error > max_bbox_error or volume_error > MAX_ERROR:
        raise RuntimeError(f"{name}: STEP/STL mismatch (bbox={box_error:.3%}, volume={volume_error:.3%})")
    print(f"validated {name}: bbox={box_error:.3%}, volume={volume_error:.3%}")
