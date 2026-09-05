"""Export the native SO-101 wrist-flex part in the upstream mesh frame, in metres."""

import sys
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad/cadquery"))
from so101_part8 import part8

shape = part8().val()
if not shape.isValid() or len(shape.Solids()) != 1:
    raise RuntimeError("native SO-101 wrist must be one valid solid")
output = ROOT / "cad/generated/so101/native_wrist_flex.stl"
output.parent.mkdir(parents=True, exist_ok=True)
# STEP/native coordinates are millimetres; official SO-101 URDF assets are metres.
cq.exporters.export(shape.scale(0.001), str(output), tolerance=0.0001, angularTolerance=0.3)
print(f"exported {output}")
