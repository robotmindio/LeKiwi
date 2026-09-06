# Part 8 physical simplification

`so101_part8_simplified.py` replaces a curved section of the lower skirts with
a planar facet between the motor rails and the lower seat. The cut starts
beyond the rails at x=-10.5 mm and stops before the seat at x=9.8 mm. Keeping
the rail support intact limits how much of this contour can be straightened.

This version modifies the exact pinned upstream STEP. It is **STEP-backed**,
not a new native reconstruction. `so101_part8.py` remains the separate native
approximation used by the robot exporter; this candidate does not replace it.

The original source is loaded once with `so101_wrist.load_part("flex_body")`
and passed to `part8_simplified(original)`. Both the source geometry and the
comparison therefore use one source of truth. The recipe contains only the
facet coordinates and extrusion; mounting geometry is not duplicated.
`cad_checks.py` shares solid comparison and STL validation/export, and
`render_stl_comparison.py` can compare other arm meshes at matching scales.

## Reproduce

From the repository root, using an interpreter with CadQuery and its VTK
dependency installed:

```sh
python cad/cadquery/test_so101_part8_simplified.py
python cad/cadquery/render_stl_comparison.py \
  cad/generated/part8/so101_part8_original.stl \
  cad/generated/part8/so101_part8_simplified.stl \
  cad/generated/part8/comparison.png
```

The check exports both STL files in millimetres and the same coordinate frame,
plus `comparison.json` with source hash, geometric measurements and mesh checks.

## What is checked

- Both solids and both boolean differences must be valid. Equal-volume boxes
  at different positions serve as a negative control for shape equality.
- No added material, so the candidate cannot introduce a new geometric
  collision at any joint angle. This preserves existing clearance; it does
  not certify that the original assembly itself is collision-free.
- The original cylindrical mounting faces retain their topology. Protected
  regions around the motor rails/heel, roof/ears, seat/foot and clip lose no
  material. No joint frame, axis or mounting location is moved.
- Both STL meshes must be closed, manifold and connected, and their volumes
  must agree with CAD within 0.1%. Export uses absolute 0.02 mm deflection.
  VTK removes zero-area facets caused by binary STL rounding; holes are not
  patched and surfaces are not smoothed. CAD volume accounting permits 1 mm³
  integration error on split spline faces, separately from the zero-addition
  shape check.

This is a conservative geometric prototype. Material, layer orientation,
supports, stiffness and fatigue have not been physically qualified. Closed
STL geometry does not establish support-free printing or equal strength.
Further structural simplification needs the intended loads and print setup.

## Serviceable redesign pilot

`so101_part8_serviceable.py` is the deeper physical redesign: one load-bearing
cradle and two removable rounded covers. It does **not** replace the production
robot exporter or the conservative candidate above.

One rounded outline generates the structural webs and both cover profiles;
one screw pattern generates the insert bosses and matching cover holes. The
right/left covers share one function. There is no new CAD dependency or general
arm-generator framework. `so101_scene.py` reuses the pinned URDF poses for checks
that can also be applied to later arm parts.

This is deliberately a **hybrid STEP-backed/native design**, not a fully native
reconstruction: clearance checking found discrepancies in the older native
mounts. The actual upstream joint ears, lower motor seat/calibration foot, motor
deck and rear rails are preserved within explicit regions. New webs, gussets and
covers use simple sketches/extrusions. Retaining the source interfaces avoids
duplicating or rounding their mechanical dimensions.

The incoming wrist-flex axis remains at (-18.1, 0, 28) mm along X; the outgoing
wrist-roll axis remains at (0, 0, -33.1) mm along Z, within the pinned URDF's
rounding. No joint transform, motor placement, link length or joint limit changes.
Changing the structure still changes mass, stiffness and dynamics: the covers
are cosmetic, not structural, and this is not a weight-optimized version.
Default assembled solid volume is about 34.5 cm³ versus 32.3 cm³ for the original
(about 7% more); printed mass also depends on material, walls and infill.

### Generate and inspect

```sh
python cad/cadquery/test_so101_part8_serviceable.py
python cad/cadquery/render_part8_serviceable.py
```

Outputs are in `cad/generated/part8-serviceable/`:

- `original.stl`, `cradle.stl`, `cover_left.stl`, `cover_right.stl`: millimetres,
  matching original assembly coordinates. Print the redesign as three parts.
- `cradle_print.stl`, `cover_left_print.stl`, `cover_right_print.stl`: the same
  parts pre-oriented on Z=0. Covers lie with their broad outside face on the bed;
  the cradle lies on its left ear. The cradle needs slicer support assessment,
  particularly the overhanging deck/seat. These are not support-free guarantees.
- `serviceable.step`: editable three-part assembly; `preview.png`: actual CAD
  comparison and exploded view, not an AI-generated concept rendering.
- `checks.json`: source hashes, interface comparisons, mesh checks and sampled
  motion-clearance results. Generated files are ignored and reproducible.

### Assembly and service

Keep the original motor and joint mounting hardware. Each cover uses three M3
countersunk screws, nominally M3×6 at the default 2 mm cover wall, and three
4 mm-long heat-set inserts. Default insert pockets are Ø4.6 × 4.2 mm deep; measure
your inserts and calibrate those parameters before printing. Check screw
engagement and tip clearance if changing wall thickness or hardware. Never drive
a screw against the bottom of a blind pocket. Inserts go into the cradle, not
the covers; avoid touching the installed servo with the insertion tool.

The cover-to-web clearance and center seam are 0.3 mm by default. After removing
three screws, each cover withdraws sideways along its outward Y direction. The
split cable opening avoids trapping a connected cable. A tie slot in the cradle
replaces the original external cable clip, so strain relief stays on the frame.
Cover vents and the open top/bottom provide access and airflow, not an ingress
or thermal rating. Full motor replacement still requires the original mounting
fasteners and potentially the adjacent joint to be removed; this is not a
verified quick-swap motor mechanism.

### What the pilot checks—and does not

The check requires zero added/removed CAD volume in the four protected interface
regions; it does not mistake equal total volume for equal shape. Every print STL
must be closed, manifold, connected and within 0.1% of CAD volume. Cover/cradle
intersections are checked at ten removal translations per side.

Actual pinned servo and immediate-neighbor meshes are checked at neutral and
across both wrist limits with angle spacing no greater than 2°. Surface vertices,
triangle centroids and edge midpoints are sampled in both directions; new
penetrations exceeding 0.08 mm relative to the upstream part fail the check.
This is finite sampling, **not** a continuous collision proof or a whole-arm
non-neighbor collision certification. Physical fit, tool access, cable bends,
strength, fatigue, print orientation/material and thermal performance still need
bench validation. Start with a fit prototype; do not assume the original payload
rating carries over to the redesigned frame.
