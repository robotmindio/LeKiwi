# Standard LeKiwi print-source recovery

`standard.scad` has one selector per reauthored solid.  For example:

```sh
openscad -D 'part="servo_wheel_hub"' -o generated/servo_wheel_hub.stl standard.scad
```

`legacy_base_plate_layer2.dxf` is an editable 2D cut contour; its SCAD file
extrudes it to the original 7 mm thickness.  The three Fusion entries retain
their original feature-history members in `LeKiwi.f3z`; their exported solids
are surface-validated in `validation/provenance.json`.

The mesh-only solids use editable DXF section stacks.  `parts.json` maps each
part to its selector and `validation/results.json` records its surface check.
The strict gate is the shared `compare_reauthored_assets.py --mesh-align`
check: 1,024 deterministic bidirectional surface samples.
Jetson's original STL has overlapping bodies, so its three watertight bodies
are checked separately and the `jetson_holder` selector is only their preview
union.
