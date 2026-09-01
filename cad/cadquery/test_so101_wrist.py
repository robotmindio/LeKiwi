"""Runnable check for the CadQuery SO-101 wrist port."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from so101_wrist import load_part, wrist_joint
from so101_wrist_flex import (
    WristFlexParameters,
    roll_mount_hole_centers,
    sts3215_envelope,
    wrist_flex,
)


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
    for name, (expected, volume) in EXPECTED_BOUNDS.items():
        part = load_part(name)
        box = part.BoundingBox()
        actual = (box.xmin, box.xmax, box.ymin, box.ymax, box.zmin, box.zmax)
        assert all(abs(value - target) < 0.001 for value, target in zip(actual, expected)), (name, actual)
        assert abs(part.Solids()[0].Volume() - volume) < 0.001, name

    native = wrist_flex().val()
    native_box = native.BoundingBox()
    assert native.isValid()
    assert len(native.Solids()) == 1
    assert abs(native_box.ymin + 20.0) < 0.001
    assert abs(native_box.ymax - 15.660093) < 0.001
    assert abs(native_box.zmin + 37.828386) < 0.001
    assert abs(native_box.zmax - 40.0) < 0.001
    assert abs(native.Volume() - EXPECTED_BOUNDS["flex_body"][1]) < 0.001
    assert native.intersect(sts3215_envelope().val()).Volume() < 0.001
    default_holes = roll_mount_hole_centers(WristFlexParameters())
    assert default_holes == (
        (-19.6, -4.95, 23.05),
        (-19.6, -4.95, 32.95),
        (-19.6, 4.95, 23.05),
        (-19.6, 4.95, 32.95),
        (19.6, -4.95, 23.05),
        (19.6, -4.95, 32.95),
        (19.6, 4.95, 23.05),
        (19.6, 4.95, 32.95),
    )
    taller = WristFlexParameters(roll_axis_height=38.0)
    assert wrist_flex(taller).val().BoundingBox().zmax == 50.0
    assert roll_mount_hole_centers(taller)[0] == (-19.6, -4.95, 33.05)
    assert len(wrist_joint().toCompound().Solids()) == 3


if __name__ == "__main__":
    main()
