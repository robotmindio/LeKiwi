"""Import the complete STEP assembly as a native FreeCAD reference document."""

import sys
from pathlib import Path

import FreeCAD as App
import Import


if len(sys.argv) != 3:
    raise SystemExit("usage: import_step_reference.py INPUT.step OUTPUT.FCStd")

source, output = map(Path, sys.argv[1:])
if not source.is_file():
    raise SystemExit(f"missing STEP file: {source}")

document = App.newDocument("LeKiwi_reference")
Import.insert(str(source), document.Name)
document.recompute()
if not document.Objects:
    raise RuntimeError("STEP import produced no objects")

output.parent.mkdir(parents=True, exist_ok=True)
document.saveAs(str(output))
print(f"saved {output} with {len(document.Objects)} objects")
