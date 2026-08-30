"""Verify FreeCAD laser-plate sources against the imported reference assembly."""

import runpy

import FreeCAD as App
import Mesh
import MeshPart


reference = App.openDocument("cad/assembly/LeKiwi_reference.FCStd")
checks = (
    ("base_plate_layer1 v5", "cad/parts/base_plate_lower.FCStd", -7.0, 0.0, "3DPrintMeshes/base_plate_layer1.stl"),
    ("base_plate_layer2 v3", "cad/parts/base_plate_upper.FCStd", 0.0, 7.0, None),
)
compare = runpy.run_path("scripts/compare_reauthored_assets.py")

for label, source_name, z_min, z_max, legacy_print in checks:
    reference_shape = next(item.Shape for item in reference.Objects if item.Label == label)
    source = App.openDocument(source_name).getObject("Extrusion").Shape
    volume_error = abs(source.Volume / reference_shape.Volume - 1)
    if volume_error >= 0.001:
        raise RuntimeError(f"{label}: volume error {volume_error:.6%}")
    if abs(source.BoundBox.XLength - reference_shape.BoundBox.XLength) >= 0.001 or abs(source.BoundBox.YLength - reference_shape.BoundBox.YLength) >= 0.001:
        raise RuntimeError(f"{label}: XY dimensions differ from reference")
    if abs(source.BoundBox.ZMin - z_min) >= 1e-9 or abs(source.BoundBox.ZMax - z_max) >= 1e-9:
        raise RuntimeError(f"{label}: source is not in the expected URDF link frame")
    print(f"{label}: volume error {volume_error:.6%}")
    if legacy_print:
        result = compare["aligned_comparison"](
            Mesh.Mesh(legacy_print),
            MeshPart.meshFromShape(Shape=source, LinearDeflection=0.05, AngularDeflection=0.2),
        )
        if result["status"] == "fail":
            raise RuntimeError(
                f"{label}: legacy-print mismatch (max={result['max_surface_error_mm']:.3f} mm, "
                f"p95={result['p95_surface_error_mm']:.3f} mm)"
            )
        print(
            f"{label}: legacy print max={result['max_surface_error_mm']:.3f} mm "
            f"p95={result['p95_surface_error_mm']:.3f} mm"
        )
