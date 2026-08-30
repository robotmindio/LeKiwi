# Manufacturing source index

[`parts.json`](parts.json) is the build record for every print asset under
`3DPrintMeshes/`, the two flat base plates, and the robot's extra LD06 mount.
It distinguishes editable source from a rendered STL instead of treating an
STL as CAD source.

The states mean:

| State | Meaning |
| --- | --- |
| `open_parametric` | Editable FreeCAD feature model is in this repository. |
| `fusion_parametric` | Original feature history is retained inside `reference/fusion/LeKiwi.f3z`; open that archive in Fusion. |
| `open_brep` | Editable STEP/FreeCAD solid, but not the original feature timeline. |
| `derived_brep` | Editable derivative of a published solid; its listed fidelity is binding. |
| `stl_only` | Only the rendered print remains. It needs a measured reauthoring before it can be called source. |

`fidelity` applies to the listed legacy print, not merely to a similarly named
part. `candidate` means a source exists but has not yet been compared to that
specific STL. `not_checked` Fusion components need an in-Fusion comparison
before they can replace a print release.

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
