"""Single-piece rounded motor cradle; no covers or external travel-stop tooth."""

from functools import lru_cache
from math import sqrt

import cadquery as cq

from so101_wrist import load_part

FRAME_OUTER_Y = 17.0
SEAT_BOTTOM_Z = -34.4
INTERFACE_REGIONS = {
    "left_joint_face": ((3, 24, 20), (-21.1, -12, 20)),
    "right_joint_face": ((3, 24, 20), (18.1, -12, 20)),
    "motor_deck_contact": ((46, 24.82, 0.06), (-10.6, -12.41, 1.49)),
    # Keep the seat and its holes, not the tooth below its underside.
    "motor_seat": ((40, 30.7, 4.11), (9.7, -15.35, SEAT_BOTTOM_Z)),
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
        .lineTo(27.2, 3.4)
        .radiusArc((35.2, -4.6), 8)
        .lineTo(35.2, -23.6)
        .radiusArc((27.2, -31.6), 8)
        .lineTo(-9.6, -31.6)
        .threePointArc((-27.1, -14.1), (-9.6, 3.4))
        .close()
        .extrude(FRAME_OUTER_Y, both=True)
    )
    crown = cq.Solid.makeCylinder(80, 100, (-40, FRAME_OUTER_Y - 80, -15.5), (1, 0, 0))
    body = body.intersect(crown).intersect(crown.mirror("XZ")).edges().fillet(2)
    ear = (
        cq.Workplane("YZ")
        .moveTo(-15, -14.1)
        .lineTo(-15, 3.4)
        .radiusArc((-12, 6.4), -3)
        .lineTo(-12, 28)
        .threePointArc((0, 40), (12, 28))
        .lineTo(12, 6.4)
        .radiusArc((15, 3.4), -3)
        .lineTo(15, -14.1)
        .close()
        .extrude(9)
        .translate((18.1, 0, 0))
        .faces(">X")
        .edges()
        .fillet(5)
    )
    body = body.union(ear).union(ear.mirror("YZ"))
    # Open front for motor insertion; relief below the rear for wrist rotation.
    body = body.cut(cq.Solid.makeBox(46.2, 24.8, 37.49, (-10.6, -12.4, -36)))
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
    region = cq.Solid.makeBox(52, 24.82, 1.91, (-16.6, -12.41, 1.49))
    body = body.cut(region).union(deck.intersect(region))
    # Clearance for the motor's top tab while withdrawing it through the front.
    entry = cq.Solid.makeCylinder(21.25, 17.1, (18.1, 0, -15.85), (1, 0, 0))
    entry = entry.intersect(cq.Solid.makeBox(17.1, 18, 2, (18.1, -9, 3.4)))
    body = body.cut(entry)
    for size, corner in INTERFACE_REGIONS.values():
        region = cq.Solid.makeBox(*size, corner)
        body = body.cut(region).union(_source().intersect(region))
    # Source counterbores are on an R7 circle, not rounded 9.9 mm spacing.
    for x in (-27.1, 21.1):
        for y in (-7 / sqrt(2), 7 / sqrt(2)):
            for z in (28 - 7 / sqrt(2), 28 + 7 / sqrt(2)):
                body = body.cut(cq.Solid.makeCylinder(2.7, 6, (x, y, z), (1, 0, 0)))
    return body.clean()
