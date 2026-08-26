"""Build editable FreeCAD extrusion sources from the validated laser DXFs."""

import sys
from pathlib import Path

import FreeCAD as App
import Part
import importDXF


PLATES = (
    ("lower", "laser-cut/generated/base_plate_lower.dxf", "cad/parts/base_plate_lower.FCStd", 92),
    ("upper", "laser-cut/generated/base_plate_upper.dxf", "cad/parts/base_plate_upper.FCStd", 96),
)


def make_plate(name, dxf_name, output_name, contour_count):
    dxf = Path(dxf_name)
    output = Path(output_name)
    if not dxf.is_file():
        raise RuntimeError(f"missing laser profile: {dxf}")

    document = App.newDocument("LeKiwiBasePlate" + name.title())
    importDXF.insert(str(dxf), document.Name)
    document.recompute()
    edges = [edge for item in document.Objects if hasattr(item, "Shape") for edge in item.Shape.Edges]
    wires = [Part.Wire(group) for group in Part.sortEdges(edges)]
    if len(wires) != contour_count or not all(wire.isClosed() for wire in wires):
        raise RuntimeError(f"{name}: expected {contour_count} closed contours, found {len(wires)}")

    faces = sorted((Part.Face(wire) for wire in wires), key=lambda face: face.Area)
    profile_shape = faces[-1].cut(Part.makeCompound(faces[:-1]))
    for item in list(document.Objects):
        document.removeObject(item.Name)

    profile = document.addObject("Part::Feature", "LaserProfile")
    profile.Label = f"{name.title()} base plate laser profile"
    profile.addProperty("App::PropertyString", "SourceDXF", "Source")
    profile.SourceDXF = str(dxf)
    profile.Shape = profile_shape
    extrusion = document.addObject("Part::Extrusion", "Extrusion")
    extrusion.Label = f"{name.title()} base plate — editable thickness"
    extrusion.Base = profile
    extrusion.DirMode = "Normal"
    extrusion.LengthFwd = 7.0
    extrusion.Solid = True
    extrusion.Placement.Base.z = -7.0 if name == "lower" else 0.0
    profile.Visibility = False
    document.recompute()
    if extrusion.Shape.isNull() or extrusion.Shape.Volume <= 0:
        raise RuntimeError(f"{name}: profile did not form a solid")
    output.parent.mkdir(parents=True, exist_ok=True)
    document.saveAs(str(output))
    print(f"saved {output}: {len(wires)} contours, {extrusion.Shape.Volume:.3f} mm^3")
    App.closeDocument(document.Name)


if len(sys.argv) != 1:
    raise SystemExit("usage: build_laser_plate_sources.py")

for plate in PLATES:
    make_plate(*plate)
