# Laser-cut base plates

`generated/` contains the editable, millimetre DXF profiles for the lower and
upper base plates used by the validated Fusion/URDF assembly. They are the
canonical cut geometry; [`base_plates.scad`](base_plates.scad) selects one for
convenient OpenSCAD export, and `build_laser_plate_sources.py` turns each into
its FreeCAD extrusion source.

`generated/print-templates/` contains matching 1:1 PDF templates for paper printing. Print at **Actual size / 100%** (never “Fit to page”); each PDF page is 216 × 213 mm. If the printer crops them, use the `*_tiled_a4.pdf` version: print both A4 pages at 100%, cut on the dashed `CORTAR/UNIR` line, and tape the two halves together.

Export a selected profile to another DXF with OpenSCAD:

```sh
openscad -D 'plate="lower"' -o /tmp/base_plate_lower.dxf base_plates.scad
openscad -D 'plate="upper"' -o /tmp/base_plate_upper.dxf base_plates.scad
```

They match the current assembly plates, including through-holes and upper-plate
cutouts. The older `3DPrintMeshes/base_plate_layer2.stl` has a different
outline; its separate editable legacy profile is tracked with the standard
reverse-engineered print sources. Set material thickness and kerf compensation
in the laser-cutter software; neither changes the 2D profile.

The native Fusion archive, whole-assembly STEP, and whole-assembly DXF are retained in `../reference/fusion/`. The Fusion archive is the only export that preserves the original feature history.
