"""Verify the locally imported FreeCAD accessory sources against their original STLs."""

from pathlib import Path

import FreeCAD as App
import Mesh
import MeshPart

from scripts.cad_utils import bounds, bounds_error
from scripts.compare_reauthored_assets import aligned_comparison

ACCESSORIES = (
    ("webcam_base_mount", Path("3DPrintMeshes/webcam_mount/webcam_mount.stl"), "Published LeKiwi STEP BREP source", 0.02),
    ("webcam_wrist_mount", Path("3DPrintMeshes/webcam_mount/webcam_mount_wrist.stl"), "Published LeKiwi STEP BREP source", 0.02),
    (
        "so100_gripper_cam_mount_insert",
        Path("3DPrintMeshes/webcam_mount/so100_gripper_cam_mount_insert.stl"),
        "SO-ARM100 STEP derivative with parametric camera-mount cuts",
        0.025,
    ),
)
MAX_ERROR = 0.02


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
        clearance = document.getObject("CameraMountM3Clearance")
        nut_trap = document.getObject("CameraMountNutTrap")
        if not clearance or abs(clearance.Radius.Value - 1.6) > 1e-9:
            raise RuntimeError(f"{name}: missing editable M3 camera-mount clearance")
        if not nut_trap or nut_trap.Polygon != 6 or abs(nut_trap.Circumradius.Value - 3.2331615) > 1e-9:
            raise RuntimeError(f"{name}: missing editable M3 hex-nut pocket")
    expected = Mesh.Mesh(str(mesh_path))
    box_error = bounds_error(bounds(final.Shape), bounds(expected))
    volume_error = abs(final.Shape.Volume / abs(expected.Volume) - 1.0)
    surface = aligned_comparison(
        expected,
        MeshPart.meshFromShape(Shape=final.Shape, LinearDeflection=0.05, AngularDeflection=0.2),
    )
    App.closeDocument(document.Name)
    if box_error > max_bbox_error or volume_error > MAX_ERROR:
        raise RuntimeError(f"{name}: STEP/STL mismatch (bbox={box_error:.3%}, volume={volume_error:.3%})")
    if surface["status"] == "fail":
        raise RuntimeError(f"{name}: surface mismatch (max={surface['max_surface_error_mm']:.3f} mm, p95={surface['p95_surface_error_mm']:.3f} mm)")
    print(
        f"validated {name}: bbox={box_error:.3%}, volume={volume_error:.3%}, "
        f"surface max={surface['max_surface_error_mm']:.3f} mm p95={surface['p95_surface_error_mm']:.3f} mm"
    )
