"""Simple part 8 cradle/covers around exact upstream mechanical interfaces."""

from dataclasses import dataclass
from math import isfinite
from functools import lru_cache

import cadquery as cq

from so101_part8 import (
    CAGE_INNER_Y,
    PLATE_INNER_X,
    PLATE_THICKNESS,
)
from so101_wrist import load_part


OUTLINE = ((-18.1, 3.4), (35.2, 3.4), (35.2, -31.6), (10.0, -31.6), (-18.1, -24.5))
WEB_THICKNESS = 3.0
WEB_WIDTH = 5.0
COVER_INNER_Y = 17.7
COVER_SCREWS = ((-8.0, -3.0), (28.0, -3.0), (18.0, -27.0))
INTERFACE_REGIONS = {
    "joint_ears": ((100, 80, 50), (-40, -40, 17.9)),
    "motor_seat": ((40, 80, 20), (9.7, -40, -50.29)),
    "motor_deck": ((46, 80, 1.92), (-10.6, -40, 1.49)),
    "rear_motor_rails": ((2.72, 24.8, 26.49), (-13.31, -12.4, -25)),
}


@dataclass(frozen=True)
class ServiceParameters:
    """Print calibration; insert dimensions must match the actual hardware."""

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


def _profile(offset: float = 0.0) -> cq.Workplane:
    """One rounded outline drives the web, hollow cover and cover exterior."""
    wire = cq.Wire.makePolygon([cq.Vector(x, 0, z) for x, z in OUTLINE], close=True)
    face = cq.Face.makeFromWires(wire)
    rounded = face.fillet2D(4.0, face.Vertices()).outerWire()
    profile = cq.Workplane("XZ").add(rounded).toPending()
    return profile.offset2D(offset) if offset else profile


@lru_cache(maxsize=1)
def _source() -> cq.Shape:
    return load_part("flex_body").Solids()[0]


def cradle(p: ServiceParameters = ServiceParameters()) -> cq.Workplane:
    p.validate()
    roof = cq.Workplane("XY").box(58.06, 24.82, 1.92).translate((6.17, 0, 2.45))
    body = roof
    for sign, base in ((-1, 1.5), (1, 3.4)):
        plate = cq.Workplane("XY").box(PLATE_THICKNESS, 24, 17.9 - base)
        body = body.union(
            plate.translate(
                (sign * (PLATE_INNER_X + PLATE_THICKNESS / 2), 0, (17.9 + base) / 2)
            )
        )
    # Preserve the actual recesses and lower motor seat, not the older native
    # approximation. Simple new geometry carries loads between these datums.
    # Flat gussets carry the ear loads into the deck/rails, not into the covers.
    for points in (
        ((-27.1, 1.51), (-13.29, 1.51), (-13.29, -24.0), (-18.1, -19.0), (-27.1, -6.5)),
        ((27.0, 3.39), (35.2, 3.39), (27.0, 18.0)),
    ):
        gusset = (
            cq.Workplane("XZ").polyline(points).close().extrude(-3).translate((0, 9, 0))
        )
        body = body.union(gusset).union(gusset.mirror("XZ"))
    web = _profile().extrude(-WEB_THICKNESS)
    web = web.cut(_profile(-WEB_WIDTH).extrude(-WEB_THICKNESS))
    web = web.translate((0, CAGE_INNER_Y, 0))
    bosses = (
        cq.Workplane("XZ")
        .pushPoints(COVER_SCREWS)
        .circle(4.5)
        .extrude(-(COVER_INNER_Y - CAGE_INNER_Y))
        .translate((0, CAGE_INNER_Y, 0))
    )
    insert_holes = (
        cq.Workplane("XZ")
        .pushPoints(COVER_SCREWS)
        .circle(p.insert_diameter / 2)
        .extrude(p.insert_depth)
        .translate((0, COVER_INNER_Y, 0))
    )
    web = web.union(bosses).cut(insert_holes)
    # A tie can loop through this slot and the large web opening; it stays on
    # the cradle when either cover is removed.
    tie_slot = (
        cq.Workplane("XZ").center(32.5, -15).rect(1.8, 4.0).extrude(30, both=True)
    )
    body = body.union(web).union(web.mirror("XZ")).cut(tie_slot)
    for size, corner in INTERFACE_REGIONS.values():
        region = cq.Solid.makeBox(*size, corner)
        body = body.cut(region).union(_source().intersect(region))
    return body.clean()


def cover(p: ServiceParameters = ServiceParameters(), *, side: int = 1) -> cq.Workplane:
    """One mirrored clamshell half. Covers withdraw along their signed Y axis."""
    p.validate()
    if side not in (-1, 1):
        raise ValueError("cover side must be -1 or 1")
    outer_y = COVER_INNER_Y + p.cover_wall
    shell = _profile(p.cover_gap + p.cover_wall).extrude(-outer_y)
    hollow = (
        _profile(p.cover_gap).extrude(-(COVER_INNER_Y + 0.1)).translate((0, -0.1, 0))
    )
    shell = shell.cut(hollow)
    shell = shell.cut(cq.Workplane("XY").box(100, p.cover_gap, 100))
    # Leave the original roof and joint ears exposed, clear of the moving roll
    # carrier. The two halves have a small clearance seam around Y=0.
    shell = shell.cut(cq.Workplane("XY").box(100, 100, 100).translate((0, 0, 53.4)))
    # The outgoing roll carrier reaches z=-32.1. Leave 0.5 mm above its swept
    # top face; the original lower seat and calibration foot stay exposed.
    shell = shell.cut(cq.Workplane("XY").box(100, 100, 100).translate((0, 0, -81.6)))
    rear_joint_exit = (
        cq.Workplane("XY")
        .box(20, 2 * (CAGE_INNER_Y + p.cover_gap), 60)
        .translate((-27.5, 0, -15))
    )
    shell = shell.cut(rear_joint_exit)
    # The structural deck has square corners; keep its upper central band
    # clear of the rounded cover return instead of thinning those motor seats.
    deck_exit = cq.Workplane("XY").box(100, 31.8, 20).translate((0, 0, 11.0))
    shell = shell.cut(deck_exit)
    seat_exit = cq.Workplane("XY").box(100, 31.8, 20).translate((0, 0, -39.8))
    shell = shell.cut(seat_exit)
    # Keep all perimeter returns outside the rectangular servo body. This
    # opening also leaves the connected servo accessible with either cap off.
    motor_exit = cq.Workplane("XY").box(46.4, 25.8, 40).translate((12.5, 0, -17))
    shell = shell.cut(motor_exit)
    screws = cq.Workplane("XZ").pushPoints(COVER_SCREWS).circle(1.6).extrude(-30)
    shell = shell.cut(screws)
    for x, z in COVER_SCREWS:
        sink = cq.Solid.makeCone(1.6, 3.1, 1.5, (x, outer_y - 1.5, z), (0, 1, 0))
        shell = shell.cut(sink)
    # The exit is split at the seam so a connected cable does not trap a cover.
    cable_exit = (
        cq.Workplane("YZ")
        .center(0, -14.4)
        .rect(14, 10)
        .extrude(10)
        .translate((33, 0, 0))
    )
    shell = shell.cut(cable_exit)
    vents = (
        cq.Workplane("XZ")
        .pushPoints([(x, -21) for x in (0, 5, 10)])
        .rect(2.5, 6)
        .extrude(30, both=True)
    )
    shell = shell.cut(vents)
    if side == -1:
        shell = shell.mirror("XZ")
    return shell.clean()


def parts(p: ServiceParameters = ServiceParameters()) -> dict[str, cq.Workplane]:
    return {
        "cradle": cradle(p),
        "cover_left": cover(p, side=-1),
        "cover_right": cover(p),
    }
