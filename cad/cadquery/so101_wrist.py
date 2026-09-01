"""Exact SO-101 follower-wrist geometry for CadQuery.

The three source STEP files retain the upstream geometry and their shared
coordinate system.  Use :func:`load_part` as the starting solid for a new
CadQuery version rather than modifying the pinned upstream submodule.
"""

from pathlib import Path

import cadquery as cq


SOURCE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "upstream"
    / "SO-ARM100"
    / "STEP"
    / "SO101"
)
PARTS = {
    "motor_holder": SOURCE_ROOT / "Motor_holder_SO101_Wrist.step",
    "flex_body": SOURCE_ROOT / "Wrist_Roll_Pitch_SO101.step",
    "roll_carrier": SOURCE_ROOT / "Follower_Specific" / "Wrist_Roll_Follower_SO101.step",
}


def load_part(name: str) -> cq.Shape:
    """Load one exact wrist component as a CadQuery shape."""
    try:
        source = PARTS[name]
    except KeyError as error:
        raise ValueError(f"unknown SO-101 wrist part: {name}") from error
    if not source.is_file():
        raise FileNotFoundError(f"missing SO-101 source: {source}")
    return cq.importers.importStep(str(source)).val()


def wrist_joint() -> cq.Assembly:
    """Return the unmodified follower wrist in its upstream STEP placement."""
    assembly = cq.Assembly(name="so101_follower_wrist")
    for name in PARTS:
        assembly.add(load_part(name), name=name)
    return assembly
