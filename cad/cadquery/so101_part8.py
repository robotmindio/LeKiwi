"""Native CadQuery replica of SO-101 part 8 (the wrist-flex body).

The upstream STEP is measurement evidence only; this module builds the part
from sketches, extrusions, cylinders, unions, and cuts.
"""

from dataclasses import dataclass

import cadquery as cq


@dataclass(frozen=True)
class Part8Parameters:
    """User calibration for the printed mounting holes, in millimetres."""

    hole_clearance: float = 0.0

    def validate(self) -> None:
        if M3_CLEARANCE + self.hole_clearance <= 0:
            raise ValueError("hole clearance produces a non-positive M3 bore")


ROLL_AXIS_Z = 28.0
PLATE_INNER_X = 18.1
PLATE_THICKNESS = 9.0
PLATE_HALF_WIDTH = 12.0
M3_HOLE_SPACING = 9.9
M3_CLEARANCE = 3.2
COUNTERBORE_DIAMETER = 5.4
AXIS_RECESS_DIAMETER = 8.4
CAGE_INNER_Y = 12.4
CAGE_OUTER_Y = 15.0


def roll_mount_hole_centers(
    parameters: Part8Parameters = Part8Parameters(),
) -> tuple[tuple[float, float, float], ...]:
    """Return the eight M3 through-bore centres as ``(x, y, z)``."""
    parameters.validate()
    offset = M3_HOLE_SPACING / 2
    plate_center = PLATE_INNER_X + PLATE_THICKNESS / 2
    return tuple(
        (x, y, ROLL_AXIS_Z + z)
        for x in (-plate_center, plate_center)
        for y in (-offset, offset)
        for z in (-offset, offset)
    )


def _mount_plate(
    parameters: Part8Parameters, x_start: float, base_z: float
) -> cq.Workplane:
    radius = PLATE_HALF_WIDTH
    plate = (
        cq.Workplane("YZ")
        .moveTo(-radius, base_z)
        .lineTo(-radius, ROLL_AXIS_Z)
        .threePointArc((0, ROLL_AXIS_Z + radius), (radius, ROLL_AXIS_Z))
        .lineTo(radius, base_z)
        .close()
        .extrude(PLATE_THICKNESS)
        .translate((x_start, 0, 0))
    )
    offset = M3_HOLE_SPACING / 2
    points = [
        (y, ROLL_AXIS_Z + z) for y in (-offset, offset) for z in (-offset, offset)
    ]
    through = (
        cq.Workplane("YZ")
        .pushPoints(points)
        .circle((M3_CLEARANCE + parameters.hole_clearance) / 2)
        .extrude(PLATE_THICKNESS + 0.2)
        .translate((x_start - 0.1, 0, 0))
    )
    left_plate = x_start < 0
    counterbore_x = x_start if left_plate else x_start + 3.0
    counterbores = (
        cq.Workplane("YZ")
        .pushPoints(points)
        .circle((COUNTERBORE_DIAMETER + parameters.hole_clearance) / 2)
        .extrude(6.1)
        .translate((counterbore_x - (0.1 if left_plate else 0), 0, 0))
    )
    recess_x = x_start + 7.0 if left_plate else x_start
    recess = (
        cq.Workplane("YZ")
        .center(0, ROLL_AXIS_Z)
        .circle((AXIS_RECESS_DIAMETER + parameters.hole_clearance) / 2)
        .extrude(2.1)
        .translate((recess_x, 0, 0))
    )
    return plate.cut(through.union(counterbores).union(recess))


def _side_skin(y: float) -> cq.Workplane:
    outer = (
        cq.Workplane("XZ")
        .moveTo(35.2, 3.4)
        .lineTo(18.1, 3.4)
        .spline(
            [
                (0.0, 2.6),
                (-7.5, 0.7),
                (-19.4, -17.5),
                (-17.1, -20.3),
                (-8.0, -26.0),
                (1.5, -29.9),
                (10.0, -32.5),
                (18.4, -34.4),
            ],
            includeCurrent=True,
        )
        .lineTo(34.4, -34.4)
        .threePointArc((34.965685, -34.165685), (35.2, -33.6))
        .close()
    )
    thickness = CAGE_OUTER_Y - CAGE_INNER_Y
    skin = outer.extrude(thickness / 2, both=True).translate((0, y, 0))
    windows = (
        cq.Workplane("XZ")
        .polyline(
            [(27.2, 0.0), (27.2, -4.25), (17.68, -12.82), (13.2, -8.78), (22.95, 0.0)]
        )
        .close()
        .extrude(thickness, both=True)
        .translate((0, y, 0))
        .union(
            cq.Workplane("XZ")
            .polyline(
                [
                    (27.2, -13.79),
                    (27.2, -18.04),
                    (17.68, -26.61),
                    (13.2, -22.57),
                    (22.95, -13.79),
                ]
            )
            .close()
            .extrude(thickness, both=True)
            .translate((0, y, 0))
        )
    )
    skinned = skin.cut(windows).val()
    outer_y = CAGE_OUTER_Y if y > 0 else -CAGE_OUTER_Y
    outer_corner = [
        edge
        for edge in skinned.Edges()
        if abs(edge.Center().x - 35.2) < 0.01
        and abs(edge.Center().y - outer_y) < 0.01
        and edge.Length() > 30
    ]
    # ponytail: 0.79 avoids degenerate facets where equal R0.8 blends meet.
    return cq.Workplane(obj=skinned.fillet(0.79, outer_corner))


def _left_bridge() -> cq.Workplane:
    bridge = (
        cq.Workplane("XZ")
        .moveTo(-18.12, 1.5)
        .lineTo(-4.133, 1.5)
        .lineTo(-4.133, 4.3)
        .lineTo(3.397, 4.3)
        .lineTo(3.397, 6.972)
        .spline(
            [(-8.0, 5.9), (-12.746, 6.007), (-16.6, 12.261)],
            includeCurrent=True,
        )
        .lineTo(-16.6, 18.0)
        .lineTo(-18.12, 18.0)
        .close()
        .extrude(10.01, both=True)
    )
    return bridge.cut(_roof_opening())


def _right_transition() -> cq.Workplane:
    """Two-radius roll-ear transition measured from the source surfaces."""
    transition = (
        cq.Workplane("XZ")
        .moveTo(27.08, 3.4)
        .lineTo(35.2, 3.4)
        .lineTo(35.2, 3.896)
        .threePointArc((34.566163, 7.39957), (32.744913, 10.458924))
        .threePointArc((28.557403, 17.494923), (27.1, 25.552))
        .close()
        .extrude(12.01, both=True)
    )
    return transition.cut(_roof_opening())


def _roof_opening() -> cq.Workplane:
    """Tapered servo-clearance opening through the cage roof."""
    return (
        cq.Workplane("XY")
        .polyline(
            [
                (-4.133, 0.0),
                (-0.048, 4.0),
                (3.952, 4.0),
                (11.1, 11.0),
                (18.1, 11.0),
                (18.1, 9.0),
                (35.4, 9.0),
                (35.4, -9.0),
                (18.1, -9.0),
                (18.1, -11.0),
                (11.1, -11.0),
                (3.952, -4.0),
                (-0.048, -4.0),
            ]
        )
        .close()
        .extrude(1.1, both=True)
        .translate((0, 0, 2.45))
    )


def _teardrop_cut(radius: float, z_start: float, depth: float) -> cq.Workplane:
    cuts = None
    tangent_x = 29.0 - 0.7 * radius
    tangent_y = (1.0 - 0.7**2) ** 0.5 * radius
    apex_x = 29.0 - 1.4295 * radius
    for y in (-10.25, 10.25):
        cut = (
            cq.Workplane("XY")
            .moveTo(apex_x, y)
            .lineTo(tangent_x, y - tangent_y)
            .threePointArc((29.0 + radius, y), (tangent_x, y + tangent_y))
            .close()
            .extrude(depth)
            .translate((0, 0, z_start))
        )
        cuts = cut if cuts is None else cuts.union(cut)
    return cuts


def _bottom_mount() -> cq.Workplane:
    floor = cq.Workplane("XY").box(21.1, 24.82, 2.2).translate((24.65, 0, -33.3))
    rails = None
    for sign in (-1, 1):
        rail = (
            cq.Workplane("YZ")
            .polyline(
                [
                    (sign * 2.6, -32.8),
                    (sign * 12.41, -32.8),
                    (sign * 12.41, -30.3),
                    (sign * 7.0, -30.3),
                    (sign * 7.0, -31.0),
                    (sign * 3.5, -32.0),
                ]
            )
            .close()
            .extrude(25.4)
            .translate((9.8, 0, 0))
        )
        rails = rail if rails is None else rails.union(rail)
    return (
        floor.union(rails)
        .cut(_teardrop_cut(2.0, -34.5, 1.8))
        .cut(_teardrop_cut(1.0, -32.9, 2.7))
    )


def part8(parameters: Part8Parameters = Part8Parameters()) -> cq.Workplane:
    """Build SO-101 part 8 without importing mesh, STEP, or BREP geometry."""
    parameters.validate()
    left_plate = _mount_plate(
        parameters,
        -PLATE_INNER_X - PLATE_THICKNESS,
        1.5,
    )
    right_plate = _mount_plate(parameters, PLATE_INNER_X, 4.9)
    side_center = (CAGE_INNER_Y + CAGE_OUTER_Y) / 2
    left_skin = _side_skin(-side_center)
    right_skin = _side_skin(side_center)

    left_bridge = _left_bridge()
    heel_profiles = {
        0: [
            (-27.1, 1.5),
            (-27.1, -6.94),
            (-25.33, -11.17),
            (-23.99, -13.34),
            (-23.33, -13.9),
            (-22.86, -13.57),
            (-22.86, 1.5),
        ],
        5: [
            (-27.1, 1.5),
            (-27.1, -6.72),
            (-24.89, -11.85),
            (-21.43, -16.47),
            (-18.67, -19.11),
            (-17.84, -19.17),
            (-17.76, 1.5),
        ],
        10: [
            (-27.1, -4.76),
            (-27.1, -6.49),
            (-24.8, -11.89),
            (-21.35, -16.52),
            (-18.67, -19.1),
            (-16.6, 2.52),
            (-16.05, 2.89),
        ],
        12.4: [
            (-16.71, -3.4),
            (-21.25, -8.68),
            (-23.92, -12.02),
            (-23.78, -13.08),
            (-21.11, -16.75),
            (-18.64, -19.12),
            (-10.41, 3.14),
        ],
    }
    heel_wires = [
        cq.Wire.makePolygon(
            [cq.Vector(x, y, z) for x, z in heel_profiles[abs(y)]],
            close=True,
        )
        for y in (-12.4, -10, -5, 0, 5, 10, 12.4)
    ]
    left_heel = cq.Workplane(obj=cq.Solid.makeLoft(heel_wires, ruled=True)).cut(
        _roof_opening()
    )
    right_transition = _right_transition()
    right_bridge = (
        cq.Workplane("XY")
        .box(17.1, 24.82, 1.62)
        .translate((26.65, 0, 4.1))
        .cut(_roof_opening())
    )
    cage_roof = (
        cq.Workplane("XY")
        .box(58.06, 24.82, 1.92)
        .translate((6.17, 0, 2.45))
        .cut(_roof_opening())
    )
    motor_rails = (
        cq.Workplane("XY")
        .box(2.7, 3.0, 25.5)
        .translate((-11.95, 10.9, -11.25))
        .union(
            cq.Workplane("XY").box(2.7, 3.0, 25.5).translate((-11.95, -10.9, -11.25))
        )
    )
    bottom_mount = _bottom_mount()
    foot = (
        cq.Workplane("XY")
        .box(7.0, 7.37, 3.428386)
        .translate((15.6, -11.385, -36.114193))
    )
    body = (
        cage_roof.union(left_bridge)
        .union(right_bridge)
        .union(right_transition)
        .union(left_plate)
        .union(right_plate)
        .union(left_heel)
        .union(left_skin)
        .union(right_skin)
        .union(motor_rails)
        .union(bottom_mount)
        .union(foot)
    )

    for x in (-6.68, 0.48):
        pad = cq.Workplane("XY").box(5.1, 5.0, 10.4).translate((x, -17.5, -15.45))
        body = body.union(pad.edges("|Y").fillet(0.8))
    return body.clean()


def wrist_flex(parameters: Part8Parameters = Part8Parameters()) -> cq.Workplane:
    """Compatibility name for the wrist-flex body."""
    return part8(parameters)
