"""Link the editable base plate solids into the FreeCAD robot assembly."""

from pathlib import Path

import FreeCAD as App


ASSEMBLY = Path("cad/assembly/LeKiwi.FCStd")
PLATES = (
    ("CadBasePlateLower", "Reauthored lower base plate", "cad/parts/base_plate_lower.FCStd", "Link_base_plate_layer1_v5"),
    ("CadBasePlateUpper", "Reauthored upper base plate", "cad/parts/base_plate_upper.FCStd", "Link_base_plate_layer2_v3"),
)


assembly = App.openDocument(str(ASSEMBLY.resolve()))
for object_name, label, source_name, metadata_name in PLATES:
    metadata = assembly.getObject(metadata_name)
    existing = assembly.getObject(object_name)
    if existing:
        metadata.CadParts = [part for part in metadata.CadParts if part != existing]
        assembly.removeObject(existing.Name)
    source = App.openDocument(str(Path(source_name).resolve()))
    part = assembly.addObject("App::Link", object_name)
    part.Label = label
    part.LinkedObject = source.getObject("Extrusion")
    part.LinkTransform = True
    metadata.CadParts = list(metadata.CadParts) + [part]

assembly.recompute()
assembly.save()
print("linked editable base plate sources into LeKiwi.FCStd")
