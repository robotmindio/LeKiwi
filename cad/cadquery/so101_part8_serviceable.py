"""Simple part 8 cradle/covers around exact upstream mechanical interfaces."""

from dataclasses import dataclass
from math import isfinite
from functools import lru_cache

import cadquery as cq

from so101_part8 import CAGE_INNER_Y
from so101_wrist import load_part


OUTLINE = ((-18.1, 3.4), (35.2, 3.4), (35.2, -31.6), (10.0, -31.6), (-18.1, -24.5))
WEB_THICKNESS = 3.0
WEB_WIDTH = 5.0
BODY_CENTER_X = 9.0
BODY_RADIUS = 32.0
COVER_BASE_Z = -31.6
COVER_TOP_Z = 3.4
COVER_SCREWS = ((9.0, 27.5), (28.0, 20.0))
INTERFACE_REGIONS = {
    "upper_fork_and_deck": ((100, 80, 60), (-40, -40, 1.49)),
    "motor_seat": ((40, 80, 20), (9.7, -40, -50.29)),
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
    """Rounded structural web; the cosmetic housing is a simple circular tube."""
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
    # Keep the original smoothly blended fork instead of introducing stepped
    # rectangular supports below the ears. Only the lower frame is rebuilt.
    gusset = (
        cq.Workplane("XZ")
        .polyline(
            ((-27.1, 1.51), (-13.29, 1.51), (-13.29, -24), (-18.1, -19), (-27.1, -6.5))
        )
        .close()
        .extrude(-3)
        .translate((0, 9, 0))
    )
    body = gusset.union(gusset.mirror("XZ"))
    web = _profile().extrude(-WEB_THICKNESS)
    web = web.cut(_profile(-WEB_WIDTH).extrude(-WEB_THICKNESS))
    web = web.translate((0, CAGE_INNER_Y, 0))
    mount_z = COVER_BASE_Z + p.cover_wall
    bosses = (
        cq.Workplane("XY")
        .pushPoints(COVER_SCREWS)
        .circle(4.2)
        .extrude(5.3)
        .translate((0, 0, mount_z))
    )
    for x, y in COVER_SCREWS:
        bridge = cq.Workplane("XY").box(8.4, y - CAGE_INNER_Y, 5.3)
        bosses = bosses.union(
            bridge.translate((x, (y + CAGE_INNER_Y) / 2, mount_z + 2.65))
        )
    insert_holes = (
        cq.Workplane("XY")
        .pushPoints(COVER_SCREWS)
        .circle(p.insert_diameter / 2)
        .extrude(p.insert_depth)
        .translate((0, 0, mount_z))
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
    radius = BODY_RADIUS + p.cover_gap + p.cover_wall
    height = COVER_TOP_Z - COVER_BASE_Z
    outside = (
        cq.Workplane("XY")
        .center(BODY_CENTER_X, 0)
        .circle(radius)
        .extrude(height)
        .edges(">Z")
        .fillet(3)
    )
    cavity = (
        cq.Workplane("XY")
        .center(BODY_CENTER_X, 0)
        .circle(radius - p.cover_wall)
        .extrude(height - p.cover_wall + 0.1)
        .edges(">Z")
        .fillet(3 - p.cover_wall)
    )
    shell = outside.cut(cavity.translate((0, 0, -0.1)))
    shell = shell.edges("<Z").fillet(0.6).translate((0, 0, COVER_BASE_Z))
    # Underside screw ledges leave the curved exterior uninterrupted. They slide
    # beneath the cradle's bosses when the two screws are removed.
    for x, y in COVER_SCREWS:
        ledge = cq.Workplane("XY").center(x, y).circle(4).extrude(p.cover_wall)
        bridge = cq.Workplane("XY").box(8, radius - y, p.cover_wall)
        ledge = ledge.union(bridge.translate((x, (radius + y) / 2, p.cover_wall / 2)))
        shell = shell.union(ledge.intersect(outside).translate((0, 0, COVER_BASE_Z)))
    half = (
        cq.Workplane("XY")
        .box(150, 80, 120)
        .translate((BODY_CENTER_X, 40 + p.cover_gap / 2, 0))
    )
    shell = shell.intersect(half)
    deck_exit = cq.Workplane("XY").box(63.3, 31.8, 20).translate((4.05, 0, 11))
    shell = shell.cut(deck_exit)
    # Only the actual rear bracket and cable exits interrupt the circular wall.
    rear_joint_exit = (
        cq.Workplane("XY")
        .box(20, 2 * (CAGE_INNER_Y + p.cover_gap), 40)
        .translate((-27.5, 0, 0))
    )
    shell = shell.cut(rear_joint_exit)
    screws = (
        cq.Workplane("XY")
        .pushPoints(COVER_SCREWS)
        .circle(1.6)
        .extrude(8)
        .translate((0, 0, COVER_BASE_Z - 0.1))
    )
    shell = shell.cut(screws)
    for x, y in COVER_SCREWS:
        sink = cq.Solid.makeCone(3.1, 1.6, 1.5, (x, y, COVER_BASE_Z), (0, 0, 1))
        shell = shell.cut(sink)
    # The exit is split at the seam so a connected cable does not trap a cover.
    cable_exit = (
        cq.Workplane("YZ")
        .center(0, -14.4)
        .sketch()
        .rect(16, 12)
        .vertices()
        .fillet(2)
        .finalize()
        .extrude(15)
        .translate((33, 0, 0))
    )
    shell = shell.cut(cable_exit)
    if side == -1:
        shell = shell.mirror("XZ")
    return shell.clean()


def parts(p: ServiceParameters = ServiceParameters()) -> dict[str, cq.Workplane]:
    return {
        "cradle": cradle(p),
        "cover_left": cover(p, side=-1),
        "cover_right": cover(p),
    }
