"""Runnable check for the CadQuery SO-101 wrist port."""

from pathlib import Path
import sys

import cadquery as cq

sys.path.insert(0, str(Path(__file__).parent))

from so101_wrist import load_part, wrist_joint
from so101_part8 import Part8Parameters, part8, roll_mount_hole_centers


EXPECTED_BOUNDS = {
    "motor_holder": (
        (-53.849907, -25.849907, -53.9, -17.0, -30.190966, 26.2),
        13880.539858,
    ),
    "flex_body": (
        (-27.1, 35.2, -20.0, 15.660093, -37.828386, 40.0),
        32312.812244,
    ),
    "roll_carrier": (
        (-35.2, 29.999999, -24.218215, 27.781786, -0.050294, 105.375),
        56619.549498,
    ),
}


def main() -> None:
    references = {}
    for name, (expected, volume) in EXPECTED_BOUNDS.items():
        part = load_part(name)
        references[name] = part.Solids()[0]
        box = part.BoundingBox()
        actual = (box.xmin, box.xmax, box.ymin, box.ymax, box.zmin, box.zmax)
        assert all(
            abs(value - target) < 0.001 for value, target in zip(actual, expected)
        ), (name, actual)
        assert abs(part.Solids()[0].Volume() - volume) < 0.001, name

    native = part8().val()
    box = native.BoundingBox()
    assert native.isValid() and len(native.Solids()) == 1
    assert all(
        abs(value - expected) < 0.7
        for value, expected in zip(
            (box.xmin, box.xmax, box.ymin, box.ymax, box.zmin, box.zmax),
            EXPECTED_BOUNDS["flex_body"][0],
        )
    )
    assert abs(native.Volume() / EXPECTED_BOUNDS["flex_body"][1] - 1) < 0.02
    vertices, triangles = references["flex_body"].tessellate(0.2, 0.3)
    sampled_triangles = (
        triangles[index * len(triangles) // 128] for index in range(128)
    )
    assert (
        max(
            native.distance(
                cq.Vertex.makeVertex(
                    *((vertices[a] + vertices[b] + vertices[c]) / 3).toTuple()
                )
            )
            for a, b, c in sampled_triangles
        )
        < 3.5
    )
    assert roll_mount_hole_centers() == (
        (-19.6, -4.95, 23.05),
        (-19.6, -4.95, 32.95),
        (-19.6, 4.95, 23.05),
        (-19.6, 4.95, 32.95),
        (19.6, -4.95, 23.05),
        (19.6, -4.95, 32.95),
        (19.6, 4.95, 23.05),
        (19.6, 4.95, 32.95),
    )
    larger_bores = part8(Part8Parameters(hole_clearance=0.2)).val()
    assert larger_bores.Volume() < native.Volume()
    assert len(wrist_joint().toCompound().Solids()) == 3


if __name__ == "__main__":
    main()
