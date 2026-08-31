"""Verify the native FreeCAD feature trees and their assembly links."""

import json
from pathlib import Path

import FreeCAD as App
import Mesh
import MeshPart

from scripts.compare_reauthored_assets import aligned_comparison

PARTS = json.loads(Path("cad/native_parts.json").read_text())


for part in PARTS:
    name = part["source"]
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
    if legacy_print := part.get("legacy_print"):
        original = Mesh.Mesh(legacy_print)
        generated = MeshPart.meshFromShape(
            Shape=final.Shape, LinearDeflection=0.05, AngularDeflection=0.2
        )
        result = aligned_comparison(original, generated)
        if result["status"] == "fail":
            raise RuntimeError(
                f"{name}: legacy-print mismatch (max={result['max_surface_error_mm']:.3f} mm, "
                f"p95={result['p95_surface_error_mm']:.3f} mm)"
            )
        print(
            f"{name}: legacy print max={result['max_surface_error_mm']:.3f} mm "
            f"p95={result['p95_surface_error_mm']:.3f} mm"
        )

assembly = App.openDocument(str(Path("cad/assembly/LeKiwi.FCStd").resolve()))
links = {item.UrdfName: item for item in assembly.getObject("LeKiwiLinks").Group}
for source in PARTS:
    name = source["source"]
    expected_source = f"cad/parts/{name}.FCStd#Final"
    for urdf_link in source["links"]:
        metadata = links[urdf_link]
        if metadata.UseCadMass or len(metadata.CadParts) != 1:
            raise RuntimeError(f"{urdf_link}: expected one geometry-only native source")
        part = metadata.CadParts[0]
        if part.TypeId != "App::Link" or getattr(part, "NativeSource", "") != expected_source:
            raise RuntimeError(f"{urdf_link}: wrong native source link")
        if not part.LinkedObject or part.LinkedObject.Name != "Final":
            raise RuntimeError(f"{urdf_link}: native source does not target Final")

print(f"validated {len(PARTS)} native feature trees and {sum(len(part['links']) for part in PARTS)} assembly links")
