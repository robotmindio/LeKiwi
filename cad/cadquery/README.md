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
