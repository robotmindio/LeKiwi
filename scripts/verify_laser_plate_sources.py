"""Verify FreeCAD laser-plate sources against the imported reference assembly."""

import FreeCAD as App


reference = App.openDocument("cad/assembly/LeKiwi_reference.FCStd")
checks = (
    ("base_plate_layer1 v5", "cad/parts/base_plate_lower.FCStd", -7.0, 0.0),
    ("base_plate_layer2 v3", "cad/parts/base_plate_upper.FCStd", 0.0, 7.0),
)

for label, source_name, z_min, z_max in checks:
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
