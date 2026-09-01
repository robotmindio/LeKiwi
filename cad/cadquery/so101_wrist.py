"""CadQuery access to the SO-101 follower wrist.

The motor holder and roll carrier load exact upstream STEP solids. Part #8 is
a native CadQuery reauthoring, with the upstream STEP kept as its fit reference.
"""

from pathlib import Path

import cadquery as cq

from so101_wrist_flex import wrist_flex


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


def wrist_joint(*, native_flex: bool = True) -> cq.Assembly:
    """Return the follower wrist, using the native part #8 reauthoring by default."""
    assembly = cq.Assembly(name="so101_follower_wrist")
    for name in PARTS:
        part = wrist_flex() if native_flex and name == "flex_body" else load_part(name)
        assembly.add(part, name=name)
    return assembly
