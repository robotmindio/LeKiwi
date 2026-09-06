"""Compare against the exact upstream source and export both checked STL files."""

import hashlib
import json
from pathlib import Path

import cadquery as cq

from cad_checks import export_stl, solid_delta
from so101_part8_simplified import part8_simplified
from so101_wrist import PARTS, load_part


def main() -> None:
    # Equal material volume must not be mistaken for equal geometry.
    box = cq.Workplane("XY").box(10, 10, 10).val()
    removed, added = solid_delta(box, box.translate((1, 0, 0)))
    assert abs(removed.Volume() - 100) < 1e-6
    assert abs(added.Volume() - 100) < 1e-6

    original = load_part("flex_body").Solids()[0]
    candidate = part8_simplified(original).val().Solids()[0]
    removed, added = solid_delta(original, candidate)
    assert added.Volume() < 1e-6, "added material needs a new motion-clearance check"
    assert 0 < removed.Volume() < original.Volume() * 0.01
    assert len(removed.Solids()) == 2, "only the two side skirts may change"
    assert removed.BoundingBox().zmax < -19.69

    # Through-bores, counterbores, axis recesses and lower screw holes retain
    # their actual upstream faces, including centres, diameters and depths.
    mounting_faces = [
        face
        for face in original.Faces()
        if face.geomType() == "CYLINDER"
        and round(face._geomAdaptor().Cylinder().Radius(), 4)
        in (1.0, 1.6, 2.0, 2.7, 4.2)
    ]
    assert len(mounting_faces) >= 22
    assert all(
        any(face.isSame(other) for other in candidate.Faces())
        for face in mounting_faces
    )

    protected = {
        "motor rails and heel": cq.Solid.makeBox(40, 24.8, 100, (-50.5, -12.4, -45)),
        "left heel": cq.Solid.makeBox(30, 60, 100, (-48, -30, -45)),
        "roll ears and roof": cq.Solid.makeBox(100, 60, 50, (-40, -30, 1.5)),
        "bottom seat and foot": cq.Solid.makeBox(40, 60, 60, (9.8, -30, -45)),
        "cable clip": cq.Solid.makeBox(14, 15, 13, (-10, -25, -22)),
    }
    for name, region in protected.items():
        overlap = removed.intersect(region)
        assert overlap.isValid() and abs(overlap.Volume()) < 1e-6, name

    output = Path(__file__).resolve().parents[1] / "generated" / "part8"
    meshes = {
        name: export_stl(shape, output / f"so101_part8_{name}.stl")
        for name, shape in (("original", original), ("simplified", candidate))
    }
    report = {
        "reference": str(
            PARTS["flex_body"].relative_to(Path(__file__).resolve().parents[1])
        ),
        "reference_sha256": hashlib.sha256(PARTS["flex_body"].read_bytes()).hexdigest(),
        "units": "mm",
        "original_volume_mm3": original.Volume(),
        "simplified_volume_mm3": candidate.Volume(),
        "removed_volume_mm3": removed.Volume(),
        "added_volume_mm3": added.Volume(),
        "volume_accounting_error_mm3": original.Volume()
        - candidate.Volume()
        - removed.Volume(),
        "protected_regions_unchanged": list(protected),
        "mounting_faces_unchanged": len(mounting_faces),
        "clearance": "No added material: no new geometric collisions at any joint angle.",
        "limitations": "No load, fatigue, thermal or physical print testing; not a strength certification.",
        "meshes": meshes,
    }
    (output / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
