# Manufacturing source index

[`parts.json`](parts.json) is the build record for every print asset under
`3DPrintMeshes/`, the two flat base plates, and the robot's extra LD06 mount.
`stl` is the compiled legacy print; `source` is its editable source record;
`validation`, when present, is the direct comparison evidence.

The states mean:

| State | Meaning |
| --- | --- |
| `open_parametric` | Editable FreeCAD or OpenSCAD model is in this repository. |
| `open_contour_stack` | Editable closed DXF profiles and a short OpenSCAD builder reconstruct the solid. |
| `open_cut_profile` | Editable DXF cut profile and its extrusion source are in this repository. |
| `open_multibody_contour_stack` | As above, with the legacy STL's real separate bodies retained separately. |
| `retained_fusion_history` | Original feature history is retained inside `reference/fusion/LeKiwi.f3z`. |
| `external_fusion_history` | Original Fusion history is available at the linked public share but is not vendored because its licence is unstated. |
| `external_fusion_history_with_patch` | The external Fusion history plus a local editable patch. |
| `open_brep` / `derived_brep` | Editable BREP solid, respectively imported or derived rather than the original timeline. |

`surface_validated` means the source was compared bidirectionally with that
specific legacy STL. `component_surface_validated` is the same check per real
body for the malformed multi-body Jetson STL. `compositional_validated` is the
documented external Fusion static-side patch proof; it is deliberately not
reported as a direct export comparison.

Flat production files are [`../laser-cut/base_plates.scad`](../laser-cut/base_plates.scad),
the generated DXFs, and the 1:1 PDFs. The older base-plate STLs are retained as
legacy prints, not as the cutting source.

[`sourced-parts.json`](sourced-parts.json) records manufacturer part numbers,
selected supplier SKUs, and the configuration membership where the BOM names a concrete purchasable part.
It deliberately does not invent an MPN for generic marketplace cables, tool
kits, fastener assortments, or batteries: their supplier SKU is the controlled
identifier until a build configuration selects an exact item.

Run the check after changing the inventory:

```sh
./scripts/verify_manufacturing_sources.sh
```
