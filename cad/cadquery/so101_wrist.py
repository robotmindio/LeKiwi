"""CadQuery access to the SO-101 follower wrist.

Part 8 is rebuilt from native CadQuery features; the other two components
retain the upstream geometry and shared coordinate system.
"""

from pathlib import Path

import cadquery as cq

from so101_part8 import part8


SOURCE_ROOT = (
    Path(__file__).resolve().parents[1] / "upstream" / "SO-ARM100" / "STEP" / "SO101"
)
PARTS = {
    "motor_holder": SOURCE_ROOT / "Motor_holder_SO101_Wrist.step",
    "flex_body": SOURCE_ROOT / "Wrist_Roll_Pitch_SO101.step",
    "roll_carrier": SOURCE_ROOT
    / "Follower_Specific"
    / "Wrist_Roll_Follower_SO101.step",
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


def wrist_joint(*, native_part8: bool = True) -> cq.Assembly:
    """Return the follower wrist, using native part 8 by default."""
    assembly = cq.Assembly(name="so101_follower_wrist")
    for name in PARTS:
        shape = part8() if native_part8 and name == "flex_body" else load_part(name)
        assembly.add(shape, name=name)
    return assembly
