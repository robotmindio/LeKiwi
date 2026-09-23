"""Photo-approximated cable windows, in upper-plate XY millimetres."""

import FreeCAD as App
import Part

# Width, height, centre X/Y, corner radius. Scale estimated from the 20 mm grid.
WINDOWS = ((60, 20, 0, 0, 4), (20, 30, 0, 50, 4))


def profiles():
    result = []
    for width, height, x, y, radius in WINDOWS:
        x0, y0 = x - width / 2, y - height / 2
        shape = Part.makePlane(width - 2 * radius, height, App.Vector(x0 + radius, y0, 0))
        shape = shape.fuse(Part.makePlane(width, height - 2 * radius, App.Vector(x0, y0 + radius, 0)))
        for cx in (x0 + radius, x0 + width - radius):
            for cy in (y0 + radius, y0 + height - radius):
                shape = shape.fuse(Part.Face(Part.Wire([Part.makeCircle(radius, App.Vector(cx, cy, 0))])))
        result.append(shape.removeSplitter())
    return result


def corrected(shape):
    """Replace cable openings only; preserve the perimeter and other screw holes."""
    shape = shape.copy()
    z, thickness = shape.BoundBox.ZMin, shape.BoundBox.ZLength
    face = max((f for f in shape.Faces if f.BoundBox.ZLength < 1e-6), key=lambda f: f.Area)
    old = [Part.Face(w) for w in face.Wires if not w.isSame(face.OuterWire) and Part.Face(w).Area > 100]
    assert len(old) in (1, 2), "Unexpected upper-plate cable window layout"

    def tool(profile):
        profile = profile.copy()
        profile.translate(App.Vector(0, 0, z - profile.BoundBox.ZMin))
        return profile.extrude(App.Vector(0, 0, thickness)) if thickness else profile

    # Rebuild the planar profile rather than fusing coincident hole boundaries.
    shape = tool(Part.Face(face.OuterWire))
    for wire in face.Wires:
        if not wire.isSame(face.OuterWire) and Part.Face(wire).Area <= 100:
            shape = shape.cut(tool(Part.Face(wire)))
    for opening in profiles():
        shape = shape.cut(tool(opening))
    return shape.removeSplitter()


def reference_mesh():
    import MeshPart
    doc = App.openDocument('cad/assembly/LeKiwi_reference.FCStd')
    shape = next(o.Shape.copy() for o in doc.Objects if o.Label == 'base_plate_layer2 v3')
    shape.translate(App.Vector(0, 0, -shape.BoundBox.ZMin))
    return MeshPart.meshFromShape(Shape=corrected(shape), LinearDeflection=0.03, AngularDeflection=0.15)


if __name__ == '__main__':
    from pathlib import Path
    doc = App.openDocument(str(Path('cad/parts/base_plate_upper.FCStd').resolve()))
    doc.LaserProfile.Shape = corrected(doc.LaserProfile.Shape)
    doc.recompute()
    assert doc.Extrusion.Shape.isValid() and len(doc.Extrusion.Shape.Solids) == 1
    assert abs(doc.Extrusion.Shape.BoundBox.ZMin) < 1e-6
    assert abs(doc.Extrusion.Shape.BoundBox.ZMax - 7) < 1e-6
    doc.save()
    assembly = App.openDocument(str(Path('cad/assembly/LeKiwi.FCStd').resolve()))
    refs = assembly.LeKiwiReferenceParts.Group
    ref = next(p for p in refs if p.UrdfLink == 'base_plate_layer2-v3')
    assembly.getObject(ref.ReferenceObject).Visibility = False
    view = assembly.getObject('InstalledUpperPlate') or assembly.addObject('App::Link', 'InstalledUpperPlate')
    view.LinkedObject = assembly.CadBasePlateUpper
    view.LinkTransform = True
    view.Placement = App.Placement(App.Vector(0, 0, 50), App.Rotation())
    view.Visibility = True
    assembly.recompute()
    assembly.save()
    print('PASS: upper plate has two rounded cable windows; assembly display updated')
