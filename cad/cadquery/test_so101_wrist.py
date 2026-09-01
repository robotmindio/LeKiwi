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


def section_area(shape: cq.Shape, plane: str, height: float) -> float:
    return cq.Workplane(plane).add(shape).section(height).val().Area()


def sampled_surface_distances(
    source: cq.Shape, target: cq.Shape, count: int = 256
) -> list[float]:
    vertices, triangles = source.tessellate(0.2, 0.3)
    distances = []
    for index in range(count):
        a, b, c = triangles[index * len(triangles) // count]
        centroid = (vertices[a] + vertices[b] + vertices[c]) / 3
        distances.append(target.distance(cq.Vertex.makeVertex(*centroid.toTuple())))
    return sorted(distances)


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
    reference = references["flex_body"]
    assert abs(native.Volume() / EXPECTED_BOUNDS["flex_body"][1] - 1) < 0.005
    for source, target in ((reference, native), (native, reference)):
        distances = sampled_surface_distances(source, target)
        assert distances[int(len(distances) * 0.95)] < 1.5

    for plane, height in (
        ("XZ", 0.0),
        ("XZ", 10.0),
        ("XY", -33.0),
        ("XY", -32.0),
        ("XY", -31.0),
        ("XY", 2.0),
        ("XY", 3.0),
    ):
        expected = section_area(reference, plane, height)
        actual = section_area(native, plane, height)
        assert abs(actual / expected - 1) < 0.08, (plane, height, actual, expected)

    radii = [
        face._geomAdaptor().Cylinder().Radius()
        for face in native.Faces()
        if face.geomType() == "CYLINDER"
    ]
    for expected in (0.8, 1.0, 2.0, 10.0, 23.0):
        assert any(abs(radius - expected) < 0.02 for radius in radii), expected
    assert sum(face.geomType() == "TORUS" for face in native.Faces()) >= 2
    assert len(cq.Workplane("XY").add(native).section(-33.0).val().Wires()) == 3
    assert len(cq.Workplane("XY").add(native).section(-32.0).val().Wires()) == 4
    assert roll_mount_hole_centers() == (
        (-22.6, -4.95, 23.05),
        (-22.6, -4.95, 32.95),
        (-22.6, 4.95, 23.05),
        (-22.6, 4.95, 32.95),
        (22.6, -4.95, 23.05),
        (22.6, -4.95, 32.95),
        (22.6, 4.95, 23.05),
        (22.6, 4.95, 32.95),
    )
    larger_bores = part8(Part8Parameters(hole_clearance=0.2)).val()
    assert larger_bores.Volume() < native.Volume() and len(larger_bores.Solids()) == 1
    try:
        part8(Part8Parameters(hole_clearance=-3.2))
    except ValueError:
        pass
    else:
        raise AssertionError("non-positive M3 bores must be rejected")
    assert len(wrist_joint().toCompound().Solids()) == 3


if __name__ == "__main__":
    main()
