"""Runnable check for the CadQuery SO-101 wrist port."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from so101_wrist import load_part, wrist_joint


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

    assert len(wrist_joint().toCompound().Solids()) == 3


if __name__ == "__main__":
    main()
