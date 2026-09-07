"""Rounded load-bearing cheeks with close-fitting, removable curved panels."""

from dataclasses import dataclass
from functools import lru_cache
from math import isfinite

import cadquery as cq

from so101_wrist import load_part

FRAME_OUTER_Y = 17.7
COVER_HEAD_Y = 23.7
COVER_BASE_Z = -31.6
COVER_TOP_Z = 3.4
COVER_SCREWS = ((-22.0, -7.0), (30.2, -22.0))  # X, Z; mirrored about Y=0
INTERFACE_REGIONS = {
    "left_joint_ear": ((9, 40, 30), (-27.1, -20, 20)),
    "right_joint_ear": ((9, 40, 30), (18.1, -20, 20)),
    "motor_deck": ((46, 24.82, 1.92), (-10.6, -12.41, 1.49)),
    "motor_seat": ((40, 30.7, 20), (9.7, -15.35, -50.29)),
    "rear_motor_rails": ((2.72, 24.8, 28.41), (-13.31, -12.4, -25)),
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
    """One sweeping cheek outline drives the frame, window and cover rim."""
    wire = (
        cq.Workplane("XZ")
        .moveTo(-27.1, 3.4)
        .lineTo(30.2, 3.4)
        .radiusArc((35.2, -1.6), 5)
        .lineTo(35.2, -26.6)
        .radiusArc((30.2, -31.6), 5)
        .lineTo(0, -31.6)
        .radiusArc((-27.1, -4.5), 27.1)
        .close()
        .val()
    )
    face = cq.Face.makeFromWires(wire)
    corner = [
        v for v in face.Vertices() if abs(v.X + 27.1) < 0.001 and abs(v.Z - 3.4) < 0.001
    ]
    profile = cq.Workplane("XZ").add(face.fillet2D(3, corner).outerWire()).toPending()
    return profile.offset2D(offset) if offset else profile


@lru_cache(maxsize=1)
def _source() -> cq.Shape:
    return load_part("flex_body").Solids()[0]


def cradle(p: ServiceParameters = ServiceParameters()) -> cq.Workplane:
    p.validate()
    cheek = _profile().extrude(-(FRAME_OUTER_Y - 11))
    cheek = cheek.cut(_profile(-9).extrude(-(FRAME_OUTER_Y - 11)))
    cheek = cheek.translate((0, 11, 0)).faces(">Y").edges().fillet(1)
    body = cheek.union(cheek.mirror("XZ"))
    # Capsules replace the old fork transitions and triangular braces. Their
    # outer rims are rounded continuously, not just at the circular ear tops.
    for side in (-1, 1):
        ear = (
            cq.Workplane("YZ")
            .center(0, 15)
            .slot2D(50, 24, 90)
            .extrude(9)
            .translate((-27.1 if side < 0 else 18.1, 0, 0))
        )
        ear = ear.faces("<X" if side < 0 else ">X").edges().fillet(5)
        if side > 0:
            ear = ear.cut(
                cq.Workplane("XY").box(100, 100, 100).translate((0, 0, -46.6))
            )
        body = body.union(ear)
    # Clear the actual rectangular servo space; source regions below restore
    # the exact supporting seats/rails, not an approximation of those contacts.
    motor = cq.Solid.makeBox(46.2, 24.8, 37.49, (-10.6, -12.4, -36))
    body = body.cut(motor)
    holes = (
        cq.Workplane("XZ")
        .pushPoints(COVER_SCREWS)
        .circle(p.insert_diameter / 2)
        .extrude(p.insert_depth)
        .translate((0, FRAME_OUTER_Y, 0))
    )
    body = body.cut(holes).cut(holes.mirror("XZ"))
    # Internal tie tunnel: the cable stays on the frame when a panel is removed.
    tie = (
        cq.Workplane("YZ")
        .center(14, -15)
        .rect(1.8, 4)
        .extrude(9.2)
        .translate((26.1, 0, 0))
    )
    body = body.cut(tie).cut(tie.mirror("XZ"))
    for size, corner in INTERFACE_REGIONS.values():
        region = cq.Solid.makeBox(*size, corner)
        body = body.cut(region).union(_source().intersect(region))
    return body.clean()


def cover(p: ServiceParameters = ServiceParameters(), *, side: int = 1) -> cq.Workplane:
    """Curved panels sit on the cheeks; no free-standing cover-mount arms."""
    p.validate()
    if side not in (-1, 1):
        raise ValueError("cover side must be -1 or 1")
    outer = cq.Solid.makeCylinder(30, 100, (-40, -3.5, -14.4), (1, 0, 0))
    inner = cq.Solid.makeCylinder(30 - p.cover_wall, 100, (-40, -3.5, -14.4), (1, 0, 0))
    shell = _profile(p.cover_gap + p.cover_wall).extrude(-40).intersect(outer)
    hollow = _profile(p.cover_gap).extrude(-40).intersect(inner)
    shell = shell.cut(hollow)
    for x, z in COVER_SCREWS:
        pad = cq.Workplane("XZ").center(x, z).circle(4.5).extrude(-30).intersect(outer)
        shell = shell.union(pad)
    envelope = cq.Solid.makeBox(
        100, 30, COVER_TOP_Z - COVER_BASE_Z, (-40, FRAME_OUTER_Y, COVER_BASE_Z)
    )
    shell = shell.intersect(envelope)
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
