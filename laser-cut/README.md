# Laser-cut base plates

`generated/` contains separate, millimetre DXF profiles for the lower and upper base plates used by the validated Fusion/URDF assembly.

Regenerate either profile with OpenSCAD:

```sh
openscad -D 'plate="lower"' -o generated/base_plate_lower.dxf base_plates.scad
openscad -D 'plate="upper"' -o generated/base_plate_upper.dxf base_plates.scad
```

These profiles are an exact 2D projection of the assembly's STL plates, including through-holes and the upper plate's cutouts. They intentionally use the URDF meshes rather than the older `3DPrintMeshes/base_plate_layer2.stl`, whose outline does not match the current assembly. Set material thickness and kerf compensation in the laser-cutter software; neither changes the 2D profile.

The native Fusion archive, whole-assembly STEP, and whole-assembly DXF are retained in `../reference/fusion/`. The Fusion archive is the only export that preserves the original feature history.
