"""Rounded load-bearing cheeks with close-fitting, removable curved panels."""

from dataclasses import dataclass
from functools import lru_cache
from math import isfinite, sqrt

import cadquery as cq

from so101_wrist import load_part

FRAME_OUTER_Y = 20.1
COVER_HEAD_Y = FRAME_OUTER_Y
COVER_SCREWS = ((-19.0, -15.5), (27.0, -15.5))  # X, Z; mirrored about Y=0
CROWN_RADIUS = 80
INTERFACE_REGIONS = {
    "left_joint_face": ((3, 24, 20), (-21.1, -12, 20)),
    "right_joint_face": ((3, 24, 20), (18.1, -12, 20)),
    "motor_deck_contact": ((46, 24.82, 0.06), (-10.6, -12.41, 1.49)),
    "motor_seat": ((40, 30.7, 20), (9.7, -15.35, -50.29)),
    "rear_motor_rails": ((2.72, 24.8, 26.6), (-13.31, -12.4, -25)),
}


@dataclass(frozen=True)
class ServiceParameters:
    """Print calibration; inserts and screw lengths must match real hardware."""

    cover_wall: float = 2.0
    cover_gap: float = 0.3
    insert_diameter: float = 4.6
    insert_depth: float = 4.2

    def validate(self) -> None:
        for name, low, high in (
            ("cover_wall", 1.6, 2.4),
            ("cover_gap", 0.2, 0.6),
            ("insert_diameter", 4.0, 5.0),
            ("insert_depth", 3.5, 4.2),
        ):
            value = getattr(self, name)
            if not isfinite(value) or not low <= value <= high:
                raise ValueError(f"{name} must be between {low} and {high} mm")


def _profile(offset: float = 0) -> cq.Workplane:
    """A single rounded outline, also used for the inset panel seam."""
    profile = (
        cq.Workplane("XZ")
        .moveTo(-9.6, 3.4)
        .lineTo(27.2, 3.4)
        .radiusArc((35.2, -4.6), 8)
        .lineTo(35.2, -23.6)
        .radiusArc((27.2, -31.6), 8)
        .lineTo(-9.6, -31.6)
        .threePointArc((-27.1, -14.1), (-9.6, 3.4))
        .close()
    )
    return profile.offset2D(offset) if offset else profile


@lru_cache(maxsize=1)
def _source() -> cq.Shape:
    return load_part("flex_body").Solids()[0]


def _crown(inset: float = 0) -> cq.Shape:
    """The frame and panels share the same gently curved side surface."""
    return cq.Solid.makeCylinder(
        CROWN_RADIUS - inset,
        100,
        (-40, FRAME_OUTER_Y - CROWN_RADIUS, -15.5),
        (1, 0, 0),
    )


def cradle(p: ServiceParameters = ServiceParameters()) -> cq.Workplane:
    p.validate()
    body = _profile().extrude(FRAME_OUTER_Y, both=True)
    body = body.intersect(_crown()).intersect(_crown().mirror("XZ"))
    body = body.edges().fillet(2)
    # Round each uninterrupted fork rim before cutting its mounting features.
    for side in (-1, 1):
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
            .translate((-27.1 if side < 0 else 18.1, 0, 0))
        )
        ear = ear.faces("<X" if side < 0 else ">X").edges().fillet(5)
        body = body.union(ear)
    # Clear the actual rectangular servo space; source regions below restore
    # the exact supporting seats/rails, not an approximation of those contacts.
    motor = cq.Solid.makeBox(46.2, 24.8, 37.49, (-10.6, -12.4, -36))
    body = body.cut(motor)
    # The neighboring roll joint passes under the rear of the cradle.
    body = body.cut(cq.Solid.makeBox(30, 24.8, 25, (-30, -12.4, -50)))
    # Rebuild the deck from its actual planar motor-contact face. Extruding
    # that footprint retains the opening but removes the old sloping fragments.
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
    deck_region = cq.Solid.makeBox(52, 24.82, 1.91, (-16.6, -12.41, 1.49))
    body = body.cut(deck_region).union(deck.intersect(deck_region))
    # Recessed panels: a shallow ledge remains around a smaller service opening.
    pocket = _profile(-4).extrude(-30).cut(_crown(2.4))
    opening = _profile(-7).extrude(25, both=True)
    body = body.cut(pocket).cut(pocket.mirror("XZ")).cut(opening)
    # Integral screw lands are below the finished side surface, not added arms.
    for x, z in COVER_SCREWS:
        land = (
            cq.Workplane("XZ")
            .center(x, z)
            .circle(4)
            .extrude(-(FRAME_OUTER_Y - 2.4 - 12.4))
            .translate((0, 12.4, 0))
        )
        body = body.union(land).union(land.mirror("XZ"))
    holes = (
        cq.Workplane("XZ")
        .pushPoints(COVER_SCREWS)
        .circle(p.insert_diameter / 2)
        .extrude(p.insert_depth)
        .translate((0, FRAME_OUTER_Y - 2.4, 0))
    )
    body = body.cut(holes).cut(holes.mirror("XZ"))
    # Internal tie tunnel: the cable stays on the frame when a panel is removed.
    tie = (
        cq.Workplane("YZ")
        .center(14, -6)
        .rect(1.8, 4)
        .extrude(5.2)
        .translate((30.1, 0, 0))
    )
    body = body.cut(tie).cut(tie.mirror("XZ"))
    for size, corner in INTERFACE_REGIONS.values():
        region = cq.Solid.makeBox(*size, corner)
        body = body.cut(region).union(_source().intersect(region))
    # Copy only the counterbore voids, not the original sculpted ear exterior.
    for x in (-27.1, 21.1):
        # Source holes lie on an R7 circle, not rounded 9.9 mm spacing.
        for y in (-7 / sqrt(2), 7 / sqrt(2)):
            for z in (28 - 7 / sqrt(2), 28 + 7 / sqrt(2)):
                bore = cq.Solid.makeCylinder(2.7, 6, (x, y, z), (1, 0, 0))
                body = body.cut(bore)
    return body.clean()


def cover(p: ServiceParameters = ServiceParameters(), *, side: int = 1) -> cq.Workplane:
    """Inset panels share the frame silhouette and a fixed screw seating depth."""
    p.validate()
    if side not in (-1, 1):
        raise ValueError("cover side must be -1 or 1")
    shell = (
        _profile(-4 - p.cover_gap)
        .extrude(-30)
        .intersect(_crown())
        .cut(_crown(p.cover_wall))
    )
    for x, z in COVER_SCREWS:
        seat = (
            cq.Workplane("XZ")
            .center(x, z)
            .circle(4 + p.cover_gap)
            .extrude(-(FRAME_OUTER_Y - 2.4))
        )
        shell = shell.cut(seat)
        pad = (
            cq.Workplane("XZ")
            .center(x, z)
            .circle(3.5)
            .extrude(-2.4)
            .translate((0, FRAME_OUTER_Y - 2.4, 0))
            .intersect(_crown())
        )
        shell = shell.union(pad)
    for x, z in COVER_SCREWS:
        bore = cq.Solid.makeCylinder(1.6, 40, (x, 0, z), (0, 1, 0))
        access = cq.Solid.makeCylinder(3.1, 20, (x, COVER_HEAD_Y, z), (0, 1, 0))
        sink = cq.Solid.makeCone(1.6, 3.1, 1.5, (x, COVER_HEAD_Y - 1.5, z), (0, 1, 0))
        shell = shell.cut(bore).cut(access).cut(sink)
    return (shell.mirror("XZ") if side < 0 else shell).clean()


def parts(p: ServiceParameters = ServiceParameters()) -> dict[str, cq.Workplane]:
    return {
        "cradle": cradle(p),
        "cover_left": cover(p, side=-1),
        "cover_right": cover(p),
    }
