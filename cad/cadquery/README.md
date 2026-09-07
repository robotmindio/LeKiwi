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
cradle and two removable curved side panels. It does **not** replace the production
robot exporter or the conservative candidate above.

The bare cradle is the primary shape: a rounded frame, softly flared fork roots,
uninterrupted outer fork rims and a planar motor deck. One rounded outline and
one R80 side surface drive both frame and inset panels. The panels meet that
same surface across a deliberate clearance seam instead of standing proud of
the frame. One side screw pattern drives the recessed lands and panel fixings;
the two panels share one mirrored builder. There are no separate triangular
braces, projecting cover-mount arms or ventilation slots.
No new dependency or arm-generator framework is added. `so101_scene.py` reuses
the pinned URDF poses for checks that can also be applied to later arm parts.

This is deliberately a **hybrid STEP-backed/native design**, not a fully native
reconstruction: clearance checking found discrepancies in the older native
mounts. Five explicit regions retain the actual left/right inner joint faces,
motor-deck contact layer, lower seat/calibration foot and rear rails. The outer
ear shape is no longer patched with entire original ear sections; the through
bores, recesses and counterbore seats are checked independently. The deck is
extruded from its original planar motor-contact footprint, keeping the relief
opening without importing the original sloping fragments. The lower internal
rear relief leaves clearance for the rotating neighboring wrist part. The
rear-rail region overlaps the rebuilt deck by 0.1 mm to avoid a coplanar-only
connection. Functional seat/rail steps and the calibration foot remain;
these are not decorative protrusions.

The incoming wrist-flex axis remains at (-18.1, 0, 28) mm along X; the outgoing
wrist-roll axis remains at (0, 0, -33.1) mm along Z, within the pinned URDF's
rounding. No joint transform, motor placement, link length or joint limit changes.
Changing the structure still changes mass, stiffness and dynamics: the covers
are cosmetic, not structural, and this is not a weight-optimized version.
The bare cradle and covered assembly are both 40.2 mm across Y, versus
53 mm for the previous stand-off panels. See `checks.json` for solid volumes;
printed mass also depends on material, walls and infill. Structural simplicity
and retained kinematics do not establish equal stiffness or payload capacity.

### Generate and inspect

```sh
python cad/cadquery/test_so101_part8_serviceable.py
python cad/cadquery/render_part8_serviceable.py
```

Outputs are in `cad/generated/part8-serviceable/`:

- `original.stl`, `cradle.stl`, `cover_left.stl`, `cover_right.stl`: millimetres,
  matching original assembly coordinates. Print the redesign as three parts.
- `cradle_print.stl`, `cover_left_print.stl`, `cover_right_print.stl`: the same
  parts pre-oriented on Z=0. Panels have their curved exterior facing up;
  their inner surfaces are curved too and require support/brim assessment.
  The cradle lies on its left ear. It also needs slicer support assessment,
  particularly the overhanging deck/seat. These are not support-free guarantees.
- `serviceable.step`: editable three-part assembly; `preview.png`: actual CAD
  original/bare-cradle/covered comparison at equal scale, not an AI concept image.
- `checks.json`: source hashes, interface comparisons, mesh checks and sampled
  motion-clearance results. Generated files are ignored and reproducible.

### Assembly and service

Keep the original motor and joint mounting hardware. Each cover uses two M3
countersunk screws from the side, nominally M3×6, and two
4 mm-long heat-set inserts. Default insert pockets are Ø4.6 × 4.2 mm deep; measure
your inserts and calibrate those parameters before printing. Check screw
engagement and tip clearance if changing wall thickness or hardware. Never drive
a screw against the bottom of a blind pocket. Inserts go into the cradle, not
the covers; install them before assembling the motors and adjacent joints.

The rim clearance is 0.3 mm by default. Screw heads seat at Y=±20.1 mm and the
panel mounting pads at Y=±17.7 mm: M3×6 gives 3.6 mm nominal engagement in the
default 4.2 mm-deep pocket. At the minimum 3.5 mm pocket depth, use shorter
hardware; the default screw would bottom out. These pad locations do not change
with panel wall calibration. Do not reuse the previous version's M3×10 screws.
After removing two screws, each panel withdraws along its outward Y direction.
A straight 6 mm shaft with 60 mm reach is checked at URDF zero; no special wrist
service rotation is needed. The access recess is only 6.2 mm in diameter; check
print calibration and use a shaft that fits, not a larger bit holder.
Handle clearance and physical fastener extraction
still need bench checking. The front motor/cable opening remains open between
the cheeks, so there is no additional cable window cut into either panel.
An internal tie tunnel high in each front rail, away from the insert pockets,
keeps strain relief on the frame and clear of the panels. There is no ingress
or thermal rating.
Full motor replacement still requires the original mounting
fasteners and potentially the adjacent joint to be removed; this is not a
verified quick-swap motor mechanism.

### What the pilot checks—and does not

The check requires zero added/removed CAD volume in the five protected contact
regions and the counterbore seating layers, plus empty Ø5.4 counterbores. It does
not mistake equal total volume for equal shape. It also guards against raised
deck fragments, the old external ear-patch seam, and proud covers. Every print STL
must be closed, manifold, connected and within 0.1% of CAD volume. Cover/cradle
intersections are checked at ten removal translations per side. Panel continuity
is checked at the former vent positions; a frame-width check guards against
projecting mounting arms. Straight screwdriver access is sampled at URDF zero,
against the neighboring visuals and the actual panels/frame.

Actual pinned servo and immediate-neighbor meshes are checked at neutral and
across both wrist limits with angle spacing no greater than 2°. Surface vertices,
triangle centroids and edge midpoints are sampled in both directions; new
penetrations exceeding 0.08 mm relative to the upstream part fail the check.
This is finite sampling, **not** a continuous collision proof or a whole-arm
non-neighbor collision certification. Physical fit, tool access, cable bends,
strength, fatigue, print orientation/material and thermal performance still need
bench validation. Start with a fit prototype; do not assume the original payload
rating carries over to the redesigned frame.
