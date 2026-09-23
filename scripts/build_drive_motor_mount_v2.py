"""Rebuild upstream v2 from native structural extrusions, holes and vent profiles."""

from pathlib import Path

import FreeCAD as App
import Mesh
import MeshPart
import Part

from scripts.build_native_part_sources import (
    mesh_slice_profile,
    new_model,
    profile,
    extrusion,
    cylinder,
    fuse,
    cut,
    finish,
)
from scripts.compare_reauthored_assets import comparison


def clean_wire(wire):
    points = [v.Point for v in wire.OrderedVertexes]
    clean = [
        b
        for i, b in enumerate(points)
        if (b - points[i - 1]).cross(points[(i + 1) % len(points)] - b).Length > 1e-7
    ]
    return Part.Wire(Part.makePolygon(clean + clean[:1]).Edges)


def build():
    target = Mesh.Mesh("3DPrintMeshes/drive_motor_mount_v2.stl")
    sliced = target.copy()
    rotation = App.Rotation(App.Vector(0, 1, 0), -90)
    sliced.transform(rotation.toMatrix())
    document, group = new_model(
        "LeKiwiDriveMotorMountV2",
        "v2 motor cage",
        Depth=34.8,
        BackThickness=5.5,
        CounterboreDepth=2.5,
        CounterboreRadius=2.0,
        MountHoleRadius=1.7,
    )

    def x_section(name, level, depth, parameter):
        shape = mesh_slice_profile(sliced, level, 0)
        shape.transformShape(rotation.inverted().toMatrix())
        item = profile(
            document,
            group,
            name + "Profile",
            name + " profile",
            shape,
            f"drive_motor_mount_v2.stl X={level} mm",
        )
        return extrusion(document, group, name, name, item, depth, False, parameter)

    sides = x_section("SideStructure", 34.7, 34.8, "Depth")
    back = x_section("BackPlate", 4, 5.5, "BackThickness")
    body = fuse(document, group, "CageBody", "V2 structural cage", [sides, back])
    holes = [
        cylinder(
            document,
            group,
            f"MountHole{i}",
            "Chassis/top mounting hole",
            1.7,
            45.5,
            (x, 0, z),
            (0, 1, 0),
            (("Radius", "MountHoleRadius"),),
        )
        for i, (x, z) in enumerate(
            ((x, z) for x in (11.05, 31.05) for z in (3.75, 43.75))
        )
    ]
    holes += [
        cylinder(
            document,
            group,
            f"Counterbore{i}",
            "Motor screw counterbore",
            2,
            2.5,
            (0, y, z),
            (1, 0, 0),
            (("Radius", "CounterboreRadius"), ("Height", "CounterboreDepth")),
        )
        for i, (y, z) in enumerate(((y, z) for y in (18.5, 43) for z in (13.5, 34)))
    ]
    inner = mesh_slice_profile(target, 9)

    def vents(shape):
        face = shape.Faces[0]
        return sorted(
            [clean_wire(w) for w in face.Wires if not w.isSame(face.OuterWire)],
            key=lambda w: Part.Face(w).CenterOfMass.x,
        )

    # ponytail: only 0.5 mm vent chamfers are sectioned (0.1 mm); analytic chamfers if tighter fidelity is needed.
    levels = [(9, 7.6041, 32.2918)]
    for j in range(5):
        levels.extend(
            [
                (7.1041 + 0.1 * j + 0.05, 7.1041 + 0.1 * j, 0.1),
                (40.3959 - 0.1 * j - 0.05, 40.3959 - 0.1 * (j + 1), 0.1),
            ]
        )
    for j, (sample, z, length) in enumerate(levels):
        wires = vents(inner if j == 0 else mesh_slice_profile(target, sample))
        assert len(wires) == 3
        for i, wire in enumerate(wires):
            face = Part.Face(wire)
            face.translate(App.Vector(0, 0, z - face.BoundBox.ZMin))
            if face.normalAt(0, 0).z < 0:
                face.reverse()
            section = profile(
                document,
                group,
                f"Vent{i}Profile{j}",
                "Editable vent contour",
                face,
                "Upstream v2 vent/chamfer section",
            )
            holes.append(
                extrusion(
                    document,
                    group,
                    f"Vent{i}Cut{j}",
                    "Vent/chamfer cut",
                    section,
                    length,
                )
            )
    final = cut(
        document,
        group,
        "Final",
        "V2 motor cage",
        body,
        fuse(document, group, "HoleTools", "V2 mounting holes and vents", holes),
    )
    document.recompute()
    assert final.Shape.isValid() and len(final.Shape.Solids) == 1
    generated = MeshPart.meshFromShape(
        Shape=final.Shape, LinearDeflection=0.03, AngularDeflection=0.15
    )
    result = comparison(target, generated)
    print(result, flush=True)
    assert result["status"] == "pass", result
    Path("cad/generated").mkdir(exist_ok=True)
    generated.write("cad/generated/drive_motor_mount_v2_native.stl")
    finish(
        document,
        group,
        final,
        Path("cad/parts/drive_motor_mount.FCStd"),
        "drive motor mount v2",
        target,
    )


if __name__ == "__main__":
    build()
