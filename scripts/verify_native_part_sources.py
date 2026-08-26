"""Verify the native FreeCAD feature trees and their assembly links."""

from pathlib import Path

import FreeCAD as App


PARTS = {
    "drive_motor_mount": (
        "drive_motor_mount-v11-2",
        "drive_motor_mount-v11-1",
        "drive_motor_mount-v11",
    ),
    "omni_wheel_mount": (
        "omni_wheel_mount-v5-2",
        "omni_wheel_mount-v5-1",
        "omni_wheel_mount-v5",
    ),
    "servo_controller_mount": ("servo_controller_mount-v3",),
    "lipo_battery_mount": ("lipo_battery_mount-v3",),
    "base_camera_mount": ("Camera-Mount-v8",),
    "wrist_camera_mount": ("Wrist-Camera-Mount-v11",),
}


for name in PARTS:
    source = App.openDocument(str((Path("cad/parts") / f"{name}.FCStd").resolve()))
    final = source.getObject("Final")
    parameters = source.getObject("Parameters")
    if not final or final.Shape.isNull() or not final.Shape.Solids:
        raise RuntimeError(f"{name}: missing native Final solid")
    if not parameters or not any(
        parameters.getTypeIdOfProperty(property_name) == "App::PropertyLength"
        for property_name in parameters.PropertiesList
    ):
        raise RuntimeError(f"{name}: missing editable dimensions")
    if final.TypeId not in ("Part::Cut", "Part::MultiFuse"):
        raise RuntimeError(f"{name}: Final is not a native Part feature")
    if "NativePart" not in final.PropertiesList or not final.NativePart:
        raise RuntimeError(f"{name}: Final is not marked as a native source")
    if any(item.TypeId == "App::Link" for item in source.Objects):
        raise RuntimeError(f"{name}: source contains an external-link wrapper")
    if not any(item.TypeId == "Part::Extrusion" for item in source.Objects):
        raise RuntimeError(f"{name}: source has no editable extrusion")

assembly = App.openDocument(str(Path("cad/assembly/LeKiwi.FCStd").resolve()))
links = {item.UrdfName: item for item in assembly.getObject("LeKiwiLinks").Group}
for name, urdf_links in PARTS.items():
    expected_source = f"cad/parts/{name}.FCStd#Final"
    for urdf_link in urdf_links:
        metadata = links[urdf_link]
        if metadata.UseCadMass or len(metadata.CadParts) != 1:
            raise RuntimeError(f"{urdf_link}: expected one geometry-only native source")
        part = metadata.CadParts[0]
        if part.TypeId != "App::Link" or getattr(part, "NativeSource", "") != expected_source:
            raise RuntimeError(f"{urdf_link}: wrong native source link")
        if not part.LinkedObject or part.LinkedObject.Name != "Final":
            raise RuntimeError(f"{urdf_link}: native source does not target Final")

print(f"validated {len(PARTS)} native feature trees and {sum(map(len, PARTS.values()))} assembly links")
