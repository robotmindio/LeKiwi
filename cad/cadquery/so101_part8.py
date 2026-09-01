"""Native CadQuery replica of SO-101 part 8 (the wrist-flex body).

The upstream STEP is measurement evidence only; this module builds the part
from sketches, extrusions, cylinders, unions, and cuts.
"""

from dataclasses import dataclass

import cadquery as cq


@dataclass(frozen=True)
class Part8Parameters:
    """Millimetre dimensions that control the printed interfaces."""

    roll_axis_z: float = 28.0
    plate_inner_x: float = 18.1
    plate_thickness: float = 9.0
    plate_half_width: float = 12.0
    m3_hole_spacing: float = 9.9
    m3_clearance: float = 3.2
    counterbore_diameter: float = 5.4
    axis_recess_diameter: float = 8.4
    hole_clearance: float = 0.0
    cage_inner_y: float = 12.4
    cage_outer_y: float = 15.0

    def validate(self) -> None:
        positive = (
            self.plate_thickness,
            self.plate_half_width,
            self.m3_hole_spacing,
            self.m3_clearance,
            self.counterbore_diameter,
            self.axis_recess_diameter,
            self.cage_inner_y,
            self.cage_outer_y,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("part 8 dimensions must be positive")
        if self.cage_outer_y <= self.cage_inner_y:
            raise ValueError("cage outer width must exceed its inner width")
        if self.counterbore_diameter <= self.m3_clearance:
            raise ValueError("M3 counterbores must be wider than their through holes")
        if self.m3_clearance + self.hole_clearance <= 0:
            raise ValueError("hole clearance produces a non-positive M3 bore")


def roll_mount_hole_centers(
    parameters: Part8Parameters = Part8Parameters(),
) -> tuple[tuple[float, float, float], ...]:
    """Return the eight M3 through-bore centres as ``(x, y, z)``."""
    offset = parameters.m3_hole_spacing / 2
    inner_center = parameters.plate_inner_x + 1.5
    return tuple(
        (x, y, parameters.roll_axis_z + z)
        for x in (-inner_center, inner_center)
        for y in (-offset, offset)
        for z in (-offset, offset)
    )


def _mount_plate(
    parameters: Part8Parameters, x_start: float, base_z: float
) -> cq.Workplane:
    radius = parameters.plate_half_width
    plate = (
        cq.Workplane("YZ")
        .moveTo(-radius, base_z)
        .lineTo(-radius, parameters.roll_axis_z)
        .threePointArc(
            (0, parameters.roll_axis_z + radius), (radius, parameters.roll_axis_z)
        )
        .lineTo(radius, base_z)
        .close()
        .extrude(parameters.plate_thickness)
        .translate((x_start, 0, 0))
    )
    offset = parameters.m3_hole_spacing / 2
    points = [
        (y, parameters.roll_axis_z + z)
        for y in (-offset, offset)
        for z in (-offset, offset)
    ]
    through = (
        cq.Workplane("YZ")
        .pushPoints(points)
        .circle((parameters.m3_clearance + parameters.hole_clearance) / 2)
        .extrude(parameters.plate_thickness + 0.2)
        .translate((x_start - 0.1, 0, 0))
    )
    left_plate = x_start < 0
    counterbore_x = x_start if left_plate else x_start + 3.0
    counterbores = (
        cq.Workplane("YZ")
        .pushPoints(points)
        .circle((parameters.counterbore_diameter + parameters.hole_clearance) / 2)
        .extrude(6.1)
        .translate((counterbore_x - (0.1 if left_plate else 0), 0, 0))
    )
    recess_x = x_start + 7.0 if left_plate else x_start
    recess = (
        cq.Workplane("YZ")
        .center(0, parameters.roll_axis_z)
        .circle((parameters.axis_recess_diameter + parameters.hole_clearance) / 2)
        .extrude(2.1)
        .translate((recess_x, 0, 0))
    )
    return plate.cut(through.union(counterbores).union(recess))


def _side_skin(parameters: Part8Parameters, y: float) -> cq.Workplane:
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
        .threePointArc((35.2, -34.0), (35.2, -33.6))
        .close()
    )
    thickness = parameters.cage_outer_y - parameters.cage_inner_y
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
    return skin.cut(windows)


def part8(parameters: Part8Parameters = Part8Parameters()) -> cq.Workplane:
    """Build SO-101 part 8 without importing mesh, STEP, or BREP geometry."""
    parameters.validate()
    left_plate = _mount_plate(
        parameters,
        -parameters.plate_inner_x - parameters.plate_thickness,
        1.5,
    )
    right_plate = _mount_plate(parameters, parameters.plate_inner_x, 4.9)
    side_center = (parameters.cage_inner_y + parameters.cage_outer_y) / 2
    body = left_plate.union(right_plate)
    body = body.union(_side_skin(parameters, -side_center)).union(
        _side_skin(parameters, side_center)
    )

    left_bridge = (
        cq.Workplane("XZ")
        .polyline(
            [
                (-18.1, 1.5),
                (-4.13, 1.5),
                (-4.13, 4.3),
                (3.4, 4.3),
                (3.4, 6.97),
                (-5.65, 5.99),
                (-12.0, 5.93),
                (-15.56, 8.59),
                (-16.6, 11.3),
                (-16.6, 18.0),
                (-18.1, 18.0),
            ]
        )
        .close()
        .extrude(parameters.cage_inner_y, both=True)
    )
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
    left_heel = cq.Workplane(obj=cq.Solid.makeLoft(heel_wires, ruled=True))
    right_quadrant = (
        cq.Workplane("XZ")
        .center(25.2, 3.896)
        .circle(10.0)
        .extrude(12.0, both=True)
        .intersect(cq.Workplane("XY").box(10.0, 24.0, 10.0).translate((30.2, 0, 8.896)))
    )
    right_bridge = cq.Workplane("XY").box(17.1, 24.8, 1.6).translate((26.65, 0, 4.1))
    cage_roof = (
        cq.Workplane("XY")
        .box(58.06, 24.8, 1.9)
        .translate((6.17, 0, 2.45))
        .cut(cq.Workplane("XY").box(39.33, 8.0, 2.1).translate((15.535, 0, 2.45)))
    )
    motor_rails = (
        cq.Workplane("XY")
        .box(2.7, 3.0, 25.5)
        .translate((-11.95, 10.9, -11.25))
        .union(
            cq.Workplane("XY").box(2.7, 3.0, 25.5).translate((-11.95, -10.9, -11.25))
        )
    )
    bottom_bridge = cq.Workplane("XY").box(21.1, 24.8, 2.2).translate((24.65, 0, -33.3))
    foot = (
        cq.Workplane("XY")
        .box(7.0, 7.37, 3.428386)
        .translate((15.6, -11.385, -36.114193))
    )
    body = (
        body.union(left_bridge)
        .union(left_heel)
        .union(right_quadrant)
        .union(right_bridge)
        .union(cage_roof)
        .union(motor_rails)
        .union(bottom_bridge)
        .union(foot)
    )

    for x in (-6.68, 0.48):
        pad = cq.Workplane("XY").box(5.1, 5.0, 10.4).translate((x, -17.5, -15.45))
        body = body.union(pad.edges("|Y").fillet(0.8))
    return body.clean()


def wrist_flex(parameters: Part8Parameters = Part8Parameters()) -> cq.Workplane:
    """Compatibility name for the wrist-flex body."""
    return part8(parameters)
