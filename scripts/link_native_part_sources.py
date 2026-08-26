"""Link the native printed-part sources into the FreeCAD robot assembly."""

import math
import re
import sys
from pathlib import Path

import FreeCAD as App


ASSEMBLY = Path("cad/assembly/LeKiwi.FCStd")
MAX_ERROR = 0.02
MODELS = (
    (
        "drive_motor_mount",
        "Part__Feature001",
        False,
        (
            ("drive_motor_mount-v11-2", "CadDriveMotorMountV11_2"),
            ("drive_motor_mount-v11-1", "CadDriveMotorMountV11_1"),
            ("drive_motor_mount-v11", "CadDriveMotorMountV11"),
        ),
    ),
    (
        "omni_wheel_mount",
        None,
        True,
        (
            ("omni_wheel_mount-v5-2", "CadOmniWheelMountV5_2"),
            ("omni_wheel_mount-v5-1", "CadOmniWheelMountV5_1"),
            ("omni_wheel_mount-v5", "CadOmniWheelMountV5"),
        ),
    ),
    ("servo_controller_mount", "Part__Feature061", False, (("servo_controller_mount-v3", "CadServoControllerMountV3"),)),
    ("lipo_battery_mount", "Part__Feature062", False, (("lipo_battery_mount-v3", "CadLiPoBatteryMountV3"),)),
    ("base_camera_mount", "Part__Feature068", False, (("Camera-Mount-v8", "CadBaseCameraMountV8"),)),
    ("wrist_camera_mount", "Part__Feature094", False, (("Wrist-Camera-Mount-v11", "CadWristCameraMountV11"),)),
)


def bounds(shape):
    box = shape.BoundBox
    return box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax


def bounds_error(left, right):
    scale = max(right[3] - right[0], right[4] - right[1], right[5] - right[2], 1.0)
    return sum(abs(a - b) for a, b in zip(left, right)) / scale


def reference_name(link_name):
    return "CadReference_" + re.sub(r"[^0-9A-Za-z_]", "_", link_name)


def app_matrix(values):
    matrix = App.Matrix()
    for row in range(4):
        for column in range(4):
            setattr(matrix, f"A{row + 1}{column + 1}", values[row][column])
    return matrix


def visual_placement(metadata):
    x, y, z = (float(value) * 1000.0 for value in metadata.VisualXYZ.split())
    roll, pitch, yaw = (float(value) for value in metadata.VisualRPY.split())
    cosine, sine = math.cos, math.sin
    return App.Placement(
        app_matrix(
            (
                (
                    cosine(yaw) * cosine(pitch),
                    cosine(yaw) * sine(pitch) * sine(roll) - sine(yaw) * cosine(roll),
                    cosine(yaw) * sine(pitch) * cosine(roll) + sine(yaw) * sine(roll),
                    x,
                ),
                (
                    sine(yaw) * cosine(pitch),
                    sine(yaw) * sine(pitch) * sine(roll) + cosine(yaw) * cosine(roll),
                    sine(yaw) * sine(pitch) * cosine(roll) - cosine(yaw) * sine(roll),
                    y,
                ),
                (-sine(pitch), cosine(pitch) * sine(roll), cosine(pitch) * cosine(roll), z),
                (0.0, 0.0, 0.0, 1.0),
            )
        )
    )


if len(sys.argv) != 1:
    raise SystemExit("usage: link_native_part_sources.py")

assembly = App.openDocument(str(ASSEMBLY.resolve()))
links_group = assembly.getObject("LeKiwiLinks")
reference_group = assembly.getObject("LeKiwiReferenceParts")
if not links_group or not reference_group:
    raise RuntimeError("missing robot metadata or migrated reference geometry")
metadata_by_name = {item.UrdfName: item for item in links_group.Group}
reference_parts = set(reference_group.Group)
managed_names = {name for _, _, _, links in MODELS for _, name in links}

for model_name, source_reference, mesh_frame, links in MODELS:
    source = App.openDocument(str((Path("cad/parts") / f"{model_name}.FCStd").resolve()))
    final = source.getObject("Final")
    if not final or final.Shape.isNull() or final.Shape.Volume <= 0:
        raise RuntimeError(f"{model_name}: missing native Final solid")
    source_shape = assembly.getObject(source_reference).Shape if source_reference else None
    for urdf_name, object_name in links:
        metadata = metadata_by_name[urdf_name]
        current = list(metadata.CadParts)
        foreign = [part for part in current if part not in reference_parts and part.Name not in managed_names]
        if foreign:
            names = ", ".join(part.Label for part in foreign)
            raise RuntimeError(f"{urdf_name}: refusing to replace non-generated CAD sources: {names}")
        existing = assembly.getObject(object_name)
        if existing:
            for link in metadata_by_name.values():
                link.CadParts = [part for part in link.CadParts if part != existing]
            assembly.removeObject(existing.Name)
        output = assembly.addObject("App::Link", object_name)
        output.Label = f"Reauthored {model_name} — {urdf_name}"
        output.LinkedObject = final
        output.LinkTransform = True
        output.addProperty("App::PropertyString", "NativeSource", "Source")
        output.NativeSource = f"cad/parts/{model_name}.FCStd#Final"
        if mesh_frame:
            output.Placement = visual_placement(metadata)
        else:
            reference = assembly.getObject(reference_name(urdf_name))
            if not reference or reference.Shape.isNull():
                raise RuntimeError(f"{urdf_name}: missing BREP reference for placement")
            output.Placement = reference.Shape.Placement * source_shape.Placement.inverse()
        metadata.CadParts = [output]
        metadata.UseCadMass = False
        assembly.recompute()
        reference = assembly.getObject(reference_name(urdf_name))
        expected = reference.Mesh if mesh_frame else reference.Shape
        box_error = bounds_error(bounds(output.Shape), bounds(expected))
        volume_error = abs(output.Shape.Volume / expected.Volume - 1.0)
        if box_error > MAX_ERROR or volume_error > MAX_ERROR:
            raise RuntimeError(f"{urdf_name}: native source mismatch (bbox={box_error:.3%}, volume={volume_error:.3%})")
        print(f"linked {urdf_name}: bbox={box_error:.3%}, volume={volume_error:.3%}")

assembly.recompute()
assembly.save()
print("linked all native LeKiwi part sources")
