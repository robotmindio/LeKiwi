"""Single-piece rounded motor cradle; no covers or external travel-stop tooth."""

from functools import lru_cache
from math import sqrt

import cadquery as cq

from so101_wrist import load_part

FRAME_OUTER_Y = 18.5
SEAT_BOTTOM_Z = -34.4
INTERFACE_REGIONS = {
    "left_joint_face": ((3, 24, 20), (-21.1, -12, 20)),
    "right_joint_face": ((3, 24, 20), (18.1, -12, 20)),
    "motor_deck_contact": ((46, 24.82, 0.06), (-10.6, -12.41, 1.49)),
    # Keep the seat and its holes, not the tooth below its underside.
    "motor_seat": ((40, 24.8, 4.11), (9.7, -12.4, SEAT_BOTTOM_Z)),
    "rear_motor_rails": ((2.72, 24.8, 26.6), (-13.31, -12.4, -25)),
}


@lru_cache(maxsize=1)
def _source() -> cq.Shape:
    return load_part("flex_body").Solids()[0]


def cradle() -> cq.Workplane:
    """One rounded shell and a mirrored fork, cut for the unchanged motor."""
    body = (
        cq.Workplane("XZ")
        .moveTo(-9.6, 3.4)
        .lineTo(35.2, 3.4)
        .radiusArc((39.2, -0.6), 4)
        .lineTo(39.2, -30.4)
        .radiusArc((35.2, -34.4), 4)
        .lineTo(19, -34.4)
        .spline([(3, -31.6)], tangents=((-1, 0), (-1, 0)), includeCurrent=True)
        .lineTo(-9.6, -31.6)
        .threePointArc((-27.1, -14.1), (-9.6, 3.4))
        .close()
        .extrude(FRAME_OUTER_Y, both=True)
    )
    crown = cq.Solid.makeCylinder(60, 100, (-40, FRAME_OUTER_Y - 60, -15.5), (1, 0, 0))
    body = body.intersect(crown).intersect(crown.mirror("XZ"))
    ear = (
        cq.Workplane("YZ")
        .moveTo(-12, -14.1)
        .lineTo(-12, 28)
        .threePointArc((0, 40), (12, 28))
        .lineTo(12, -14.1)
        .close()
        .extrude(9)
        .translate((18.1, 0, 0))
        .faces(">X")
        .edges("%CIRCLE")
        .fillet(5)
    )
    body = body.union(ear).union(ear.mirror("YZ"))
    roots = [
        edge
        for edge in body.val().Edges()
        if abs(abs(edge.Center().x) - 18.1) < 1e-5
        and edge.BoundingBox().zmax < 4
        and edge.Length() > 20
    ]
    assert len(roots) == 2, "expected two fork-to-body junctions"
    body = cq.Workplane(obj=body.val().fillet(3, roots))
    rim = [edge for edge in body.val().Edges() if abs(edge.Center().y) > 14]
    body = cq.Workplane(obj=body.val().fillet(3, rim))
    # Open front for motor insertion; relief below the rear for wrist rotation.
    body = body.cut(cq.Solid.makeBox(60, 24.8, 37.49, (-10.6, -12.4, -36)))
    body = body.cut(cq.Solid.makeBox(30, 24.8, 25, (-30, -12.4, -50)))

    # A planar deck retains the original motor-contact footprint and access
    # opening, without the original sculpted roof fragments.
    deck_face = next(
        face
        for face in _source().Faces()
        if face.geomType() == "PLANE"
        and abs(face.Center().z - 1.5) < 1e-6
        and face.Area() > 600
    )
    deck = cq.Solid.extrudeLinear(
        deck_face.outerWire(), deck_face.innerWires(), (0, 0, 1.9)
    )
    deck = cq.Workplane(obj=deck).faces(">Z").edges().fillet(0.6).val()
    region = cq.Solid.makeBox(60, 24.82, 1.91, (-16.6, -12.41, 1.49))
    body = body.cut(region).union(deck.intersect(region))
    # Clearance for the motor's top tab while withdrawing it through the front.
    entry = cq.Solid.makeCylinder(21.25, 29, (14.1, 0, -15.85), (1, 0, 0))
    entry = entry.intersect(cq.Solid.makeBox(29, 18, 2, (14.1, -9, 3.4)))
    body = body.cut(entry)
    body = body.cut(cq.Solid.makeBox(4, 24, 2, (14.1, -12, 3.4)))
    for size, corner in INTERFACE_REGIONS.values():
        region = cq.Solid.makeBox(*size, corner)
        body = body.cut(region).union(_source().intersect(region))
    # Source counterbores are on an R7 circle, not rounded 9.9 mm spacing.
    for x in (-27.1, 21.1):
        for y in (-7 / sqrt(2), 7 / sqrt(2)):
            for z in (28 - 7 / sqrt(2), 28 + 7 / sqrt(2)):
                body = body.cut(cq.Solid.makeCylinder(2.7, 6, (x, y, z), (1, 0, 0)))
    return body.clean()
