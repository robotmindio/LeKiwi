"""Link the native printed-part sources into the FreeCAD robot assembly."""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import FreeCAD as App

from scripts.cad_utils import bounds, bounds_error, urdf_matrix


ASSEMBLY = Path("cad/assembly/LeKiwi.FCStd")
NATIVE_PARTS = Path("cad/native_parts.json")
MAX_ERROR = 0.02


def reference_name(link_name):
    return "CadReference_" + re.sub(r"[^0-9A-Za-z_]", "_", link_name)


def visual_placement(metadata):
    origin = ET.Element("origin", {"xyz": metadata.VisualXYZ, "rpy": metadata.VisualRPY})
    return App.Placement(urdf_matrix(origin))


if len(sys.argv) != 1:
    raise SystemExit("usage: link_native_part_sources.py")

assembly = App.openDocument(str(ASSEMBLY.resolve()))
links_group = assembly.getObject("LeKiwiLinks")
reference_group = assembly.getObject("LeKiwiReferenceParts")
if not links_group or not reference_group:
    raise RuntimeError("missing robot metadata or migrated reference geometry")
metadata_by_name = {item.UrdfName: item for item in links_group.Group}
reference_parts = set(reference_group.Group)
models = json.loads(NATIVE_PARTS.read_text())
managed_names = {name for model in models for name in model["links"].values()}

for model in models:
    model_name = model["source"]
    source_reference = model["reference_object"]
    mesh_frame = model["mesh_frame"]
    source = App.openDocument(str((Path("cad/parts") / f"{model_name}.FCStd").resolve()))
    final = source.getObject("Final")
    if not final or final.Shape.isNull() or final.Shape.Volume <= 0:
        raise RuntimeError(f"{model_name}: missing native Final solid")
    source_shape = assembly.getObject(source_reference).Shape if source_reference else None
    for urdf_name, object_name in model["links"].items():
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
