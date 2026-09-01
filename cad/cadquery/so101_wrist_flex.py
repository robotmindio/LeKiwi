"""Native CadQuery reauthoring of SO-101 part #8, the wrist-flex body.

The model keeps the upstream roll-servo and flex-horn datums as named
parameters, so a new wrist length or skin can be generated without editing a
STEP BREP. It is a new structural design, not a surface-equivalent clone.
"""

from dataclasses import dataclass
from math import cos, radians, sin

import cadquery as cq


@dataclass(frozen=True)
class WristFlexParameters:
    """Millimetre dimensions for the SO-101 follower wrist-flex body."""

    roll_axis_height: float = 28.0
    roll_side_gap: float = 36.2
    side_plate_thickness: float = 3.0
    roll_mount_radius: float = 12.0
    roll_axis_bore_diameter: float = 8.4
    roll_mount_hole_spacing: float = 9.9
    m3_clearance_diameter: float = 3.2
    flex_axis_x: float = 25.2
    flex_axis_height: float = 3.896
    flex_horn_radius: float = 10.0
    flex_horn_bore_diameter: float = 8.4
    flex_horn_bolt_radius: float = 7.0
    body_depth: float = 35.660093
    body_center_y: float = -2.1699535
    lower_web_height: float = -34.4
    lower_foot_height: float = 4.828386
    motor_length: float = 46.0
    motor_width: float = 24.0
    motor_height: float = 39.0
    motor_pocket_width: float = 25.398851
    motor_center_x: float = 12.5
    motor_center_z: float = -14.9
    flex_horn_mount_y: float = -16.1
    flex_horn_mount_thickness: float = 3.0

    def validate(self) -> None:
        if self.roll_side_gap <= 0 or self.body_depth <= 0:
            raise ValueError("roll-side gap and body depth must be positive")
        if self.side_plate_thickness <= 0 or self.roll_mount_radius <= 0:
            raise ValueError("side-plate thickness and roll-mount radius must be positive")
        if self.m3_clearance_diameter <= 0 or self.m3_clearance_diameter >= self.roll_mount_hole_spacing:
            raise ValueError("invalid roll-servo M3 hole pattern")
        if self.flex_horn_bore_diameter >= 2 * self.flex_horn_radius:
            raise ValueError("flex-horn bore consumes the mounting boss")
        if self.motor_pocket_width < self.motor_width:
            raise ValueError("motor pocket is narrower than the STS3215 envelope")


def roll_mount_hole_centers(
    parameters: WristFlexParameters,
) -> tuple[tuple[float, float, float], ...]:
    """Return the eight M3 roll-servo holes as ``(x, y, z)`` centres."""
    offset = parameters.roll_mount_hole_spacing / 2
    plate_offset = parameters.roll_side_gap / 2
    return tuple(
        (x, y, parameters.roll_axis_height + z)
        for x in (
            -plate_offset - parameters.side_plate_thickness / 2,
            plate_offset + parameters.side_plate_thickness / 2,
        )
        for y in (-offset, offset)
        for z in (-offset, offset)
    )


def _roll_side_plate(parameters: WristFlexParameters, x_start: float) -> cq.Workplane:
    radius = parameters.roll_mount_radius
    plate = (
        cq.Workplane("YZ")
        .moveTo(-radius, 0)
        .lineTo(-radius, parameters.roll_axis_height)
        .threePointArc((0, parameters.roll_axis_height + radius), (radius, parameters.roll_axis_height))
        .lineTo(radius, 0)
        .close()
        .extrude(parameters.side_plate_thickness)
        .translate((x_start, 0, 0))
    )
    cutter = (
        cq.Workplane("YZ")
        .center(0, parameters.roll_axis_height)
        .circle(parameters.roll_axis_bore_diameter / 2)
        .extrude(parameters.side_plate_thickness * 2, both=True)
        .translate((x_start, 0, 0))
    )
    plate_center = x_start + parameters.side_plate_thickness / 2
    for x, y, z in roll_mount_hole_centers(parameters):
        if abs(x - plate_center) > 1e-9:
            continue
        cutter = cutter.union(
            cq.Workplane("YZ")
            .center(y, z)
            .circle(parameters.m3_clearance_diameter / 2)
            .extrude(parameters.side_plate_thickness * 2, both=True)
            .translate((x_start, 0, 0))
        )
    return plate.cut(cutter)


def _flex_horn(parameters: WristFlexParameters) -> cq.Workplane:
    horn = (
        cq.Workplane("XZ")
        .center(parameters.flex_axis_x, parameters.flex_axis_height)
        .circle(parameters.flex_horn_radius)
        .extrude(parameters.flex_horn_mount_thickness)
        .translate((0, parameters.flex_horn_mount_y, 0))
    )
    cutter = (
        cq.Workplane("XZ")
        .center(parameters.flex_axis_x, parameters.flex_axis_height)
        .circle(parameters.flex_horn_bore_diameter / 2)
        .extrude(parameters.flex_horn_mount_thickness)
        .translate((0, parameters.flex_horn_mount_y, 0))
    )
    for angle in range(0, 360, 90):
        cutter = cutter.union(
            cq.Workplane("XZ")
            .center(
                parameters.flex_axis_x + parameters.flex_horn_bolt_radius * cos(radians(angle)),
                parameters.flex_axis_height + parameters.flex_horn_bolt_radius * sin(radians(angle)),
            )
            .circle(parameters.m3_clearance_diameter / 2)
            .extrude(parameters.flex_horn_mount_thickness)
            .translate((0, parameters.flex_horn_mount_y, 0))
        )
    return horn.cut(cutter)


def sts3215_envelope(parameters: WristFlexParameters = WristFlexParameters()) -> cq.Workplane:
    """Return the measured STS3215 no-horn installation envelope."""
    return (
        cq.Workplane("XY")
        .box(parameters.motor_length, parameters.motor_width, parameters.motor_height)
        .translate((parameters.motor_center_x, 0, parameters.motor_center_z))
    )


def _motor_pocket(parameters: WristFlexParameters) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(parameters.motor_length, parameters.motor_pocket_width, parameters.motor_height)
        .translate((parameters.motor_center_x, 0, parameters.motor_center_z))
    )


def wrist_flex(parameters: WristFlexParameters = WristFlexParameters()) -> cq.Workplane:
    """Build the native, parameterized wrist-flex body."""
    parameters.validate()
    outer = parameters.roll_side_gap / 2 + parameters.side_plate_thickness
    crossbar = (
        cq.Workplane("XY")
        .box(2 * outer, parameters.body_depth, 6)
        .translate((0, parameters.body_center_y, 3))
    )
    # ponytail: straight truss web; replace with a measured load-path profile if proof testing finds flex.
    body = (
        cq.Workplane("XZ")
        .polyline(
            [
                (-outer, 3),
                (outer, 3),
                (
                    parameters.flex_axis_x + parameters.flex_horn_radius,
                    parameters.flex_axis_height - parameters.flex_horn_radius,
                ),
                (parameters.flex_axis_x + parameters.flex_horn_radius, parameters.lower_web_height + 4),
                (10, parameters.lower_web_height),
                (-12, parameters.lower_web_height + 7),
                (-outer, -10),
            ]
        )
        .close()
        .extrude(parameters.body_depth / 2, both=True)
        .translate((0, parameters.body_center_y, 0))
    )
    foot = (
        cq.Workplane("XY")
        .box(12, 6, parameters.lower_foot_height)
        .translate(
            (
                14,
                parameters.body_center_y - parameters.body_depth / 2 + 3,
                parameters.lower_web_height + 1.4 - parameters.lower_foot_height / 2,
            )
        )
    )
    left = _roll_side_plate(parameters, -outer)
    right = _roll_side_plate(parameters, parameters.roll_side_gap / 2)
    cage = body.union(crossbar).union(foot).union(left).union(right)
    return cage.cut(_motor_pocket(parameters)).union(_flex_horn(parameters))
