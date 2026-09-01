"""Simplified, kinematically compatible alternative to SO-101 part 8."""

import cadquery as cq

from so101_part8 import (
    CAGE_INNER_Y,
    PLATE_INNER_X,
    PLATE_THICKNESS,
    Part8Parameters,
    _bottom_mount,
    _mount_plate,
)


WALL_THICKNESS = 3.0
FRAME_TOP_Z = 3.4
FRAME_BOTTOM_Z = -34.4
FRAME_RIGHT_X = 35.2


def _side_wall(y: float) -> cq.Workplane:
    wall = (
        cq.Workplane("XZ")
        .polyline(
            [
                (-PLATE_INNER_X, FRAME_TOP_Z),
                (FRAME_RIGHT_X, FRAME_TOP_Z),
                (FRAME_RIGHT_X, FRAME_BOTTOM_Z),
                (12.0, FRAME_BOTTOM_Z),
                (-PLATE_INNER_X, -8.0),
            ]
        )
        .close()
        .extrude(WALL_THICKNESS / 2, both=True)
        .translate((0, y, 0))
    )
    window = (
        cq.Workplane("XZ")
        .center(13.0, -13.0)
        .sketch()
        .rect(35.0, 20.0)
        .vertices()
        .fillet(6.0)
        .finalize()
        .extrude(WALL_THICKNESS, both=True)
        .translate((0, y, 0))
    )
    return wall.cut(window).edges("|Y").fillet(2.0)


def _top_frame() -> cq.Workplane:
    outer_y = CAGE_INNER_Y + WALL_THICKNESS
    back = (
        cq.Workplane("XY")
        .box(14.2, 2 * outer_y, 2.0)
        .translate((-11.1, 0, FRAME_TOP_Z - 0.9))
    )
    rails = None
    for y in (-outer_y + WALL_THICKNESS / 2, outer_y - WALL_THICKNESS / 2):
        rail = (
            cq.Workplane("XY")
            .box(FRAME_RIGHT_X + 4.1, WALL_THICKNESS, 2.0)
            .translate(((FRAME_RIGHT_X - 4.1) / 2, y, FRAME_TOP_Z - 0.9))
        )
        rails = rail if rails is None else rails.union(rail)

    shoulders = None
    for y in (-13.6, 13.6):
        shoulder = (
            cq.Workplane("XY")
            .box(9.2, 3.6, 1.2)
            .translate((22.6, y, FRAME_TOP_Z + 0.1))
        )
        shoulders = shoulder if shoulders is None else shoulders.union(shoulder)
    return back.union(rails).union(shoulders)


def _servo_rails() -> cq.Workplane:
    rails = None
    for y in (-10.9, 10.9):
        rail = cq.Workplane("XY").box(2.7, 3.0, 25.5).translate((-11.95, y, -11.25))
        rails = rail if rails is None else rails.union(rail)
    return rails


def part8_simplified(
    parameters: Part8Parameters = Part8Parameters(),
) -> cq.Workplane:
    """Build the simpler alternative without changing the original part."""
    parameters.validate()
    outer_y = CAGE_INNER_Y + WALL_THICKNESS
    body = (
        _top_frame()
        .union(_side_wall(-outer_y + WALL_THICKNESS / 2))
        .union(_side_wall(outer_y - WALL_THICKNESS / 2))
        .union(
            _mount_plate(
                parameters,
                -PLATE_INNER_X - PLATE_THICKNESS,
                FRAME_TOP_Z,
            )
        )
        .union(_mount_plate(parameters, PLATE_INNER_X, FRAME_TOP_Z))
        .union(_bottom_mount())
        .union(_servo_rails())
    )
    return body.clean()


def _self_check() -> None:
    shape = part8_simplified().val()
    assert shape.isValid() and len(shape.Solids()) == 1
    assert shape.Volume() > 0
    side_section = cq.Workplane("XZ").add(_side_wall(0)).section(0).val()
    assert len(side_section.Wires()) == 2
    larger_bores = part8_simplified(Part8Parameters(hole_clearance=0.2)).val()
    assert larger_bores.isValid() and larger_bores.Volume() < shape.Volume()


if __name__ == "__main__":
    _self_check()
