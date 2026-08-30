# Dynamixel print sources

`parts.json` is the source and validation manifest for every Dynamixel-specific
print.  It records the original STL's unit conversion, the canonical editable
source, and the bidirectional surface-comparison result.  Native Fusion files
remain at [the public Fusion share](https://a360.co/44YAcMn): it has no stated
redistribution licence, so this repository stores stable component identifiers
and hashes instead of a copy.

## Local sources

The three legacy prints without matching exportable Fusion bodies are editable
locally.  `dynamixel.scad` reconstructs the arm and drive mount from closed DXF
sections; `lipo_battery_mount.scad` is a direct parametric tray model.  All
dimensions are millimetres.  Build ignored STLs locally with:

```sh
cd cad/reverse_engineered/dynamixel
openscad -D 'part="dynamixel_modified_base_arm"' -o generated/dynamixel_modified_base_arm.stl dynamixel.scad
openscad -D 'part="dynamixel_drive_motor_mount"' -o generated/dynamixel_drive_motor_mount.stl dynamixel.scad
openscad -o generated/lipo_battery_mount.stl lipo_battery_mount.scad
```

The arm uses the coarsest tested 16-section stack that passes the 0.25 mm maximum
and 0.10 mm p95 surface gate.  The drive mount uses the coarsest tested passing
uniform stack: 230 sections at 0.239565210757 mm.

## Static-side patch

Open the `Static Side Gripper` source from the public Fusion share, select its
small BRep body, and run `patch_static_legacy_hole.py` from Fusion's Scripts and
Add-Ins dialog.  It adds the one missing legacy R3.149941806669 mm finite
through-hole as a native Combine/Cut feature.  Export the patched body together
with the unchanged large Static Side Gripper body to produce the original
two-body print.

`validation/verify_static_composition.py` is an independently reproducible
composition proof.  Run it in FreeCAD's Python console after setting
`sys.argv` to the path of an uncommitted export of the current unpatched small
body; it checks that the current source passes everywhere other than exactly the
52 fitted target hole faces, then verifies those faces against the patch's
radius and endpoints.  It reports `compositional_pass`, deliberately distinct
from a direct patched-export comparison: the public STEP proxy has a mismatched
BRep cutter span and is not used as an export surrogate.

```python
import runpy, sys
sys.argv = ["verify_static_composition.py", "/absolute/path/to/static_a.stl"]
runpy.run_path("/absolute/path/to/verify_static_composition.py", run_name="__main__")
```
