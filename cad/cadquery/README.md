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

## Single-piece rounded redesign

`so101_part8_serviceable.py` retains its historical filename but now builds
**one piece**: a smooth motor cradle with integral curved sides and a mirrored
fork. The cover builders, seams, windows, screw bosses, inserts, cable-tie
tunnels and cover calibration parameters are gone. The outside is 34 mm wide,
versus 40.2 mm for the last covered version. The motor opening stays open;
this is not a sealed enclosure or a lightweight optimization.

The bottom tooth is removed at the user's request. It previously contacted the
rotating wrist outside the configured motion range, consistent with a travel
stop. **That mechanical stop no longer exists.** The software limits have not
been expanded; do not assume the old physical end-stop/calibration behavior.

The incoming wrist-flex axis stays at (-18.1, 0, 28) mm along X and outgoing
wrist-roll at (0, 0, -33.1) mm along Z, within the pinned URDF's rounding.
Motor placement, joint transforms, link lengths and software limits are unchanged.
Mass, stiffness and payload capacity are not guaranteed equivalent.

This remains a hybrid native/STEP-backed design. Native rounded geometry defines
the shell and fork; exact source patches retain the motor contacts, rails,
joint faces and mounting holes. The lower-seat patch ends at Z=-34.4 mm rather
than importing the tooth underneath. The deck is planar, retaining the original
contact footprint and access opening. The original source is never modified.

### Generate and inspect

```sh
python cad/cadquery/test_so101_part8_serviceable.py
python cad/cadquery/render_part8_serviceable.py
```

Current outputs are in **`cad/generated/part8-smooth/`**:

- `original.stl` and `cradle.stl`: matching original assembly coordinates, mm.
- `cradle_print.stl`: the same single part oriented with its left ear down.
  Inspect supports for the deck and lower seat in your slicer; this is not a
  support-free or physically qualified print.
- `cradle.step`: editable solid.
- `preview.png`: actual original/redesign/underside views at equal scale.
- `checks.json`: source hashes, exact-interface and sampled-clearance results.

The older `part8-serviceable/` generated files are superseded. They are not
outputs of this builder; do not print their covers for this version.

### Assembly and checks

Use the original motor/joint hardware. There are no additional cover screws or
heat-set inserts. The open front provides motor access; the fork-root opening
clears the motor's top tab. Removing the motor still requires its fasteners and
possibly the neighboring joint to be removed.

Checks compare added/removed material in the five protected contact regions and
counterbore seating layers—not just total volume. They also check the empty
counterbores, absence of the tooth and old raised deck fragments, uninterrupted
side walls, and absence of the old fork-patch seam. Each STL must be closed,
manifold, connected and within 0.1% of CAD volume.

The actual pinned motor and immediate neighboring meshes are sampled across
259 configurations, with wrist angle spacing no greater than 2°. New
penetration beyond 0.08 mm relative to upstream fails. Front motor entry is
also compared to upstream in both sampling directions at 61 translations over
60 mm. The source model already has clip/guide interference, so this is **not**
proof of a rigid, force-free insertion path.

These are finite geometric checks, not continuous swept-volume proof, whole-arm
collision certification, or bench validation. Physical assembly, cable routing,
print fit, cooling, strength and fatigue still need testing. Start with a fit
prototype and retain the software motion limits.
