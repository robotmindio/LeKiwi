"""Place the six existing rods on the operator-identified chassis holes.

Run with FreeCADCmd. Default is a read-only check; --apply updates the assembly.
The original LeKiwi_reference.FCStd remains untouched.
"""

import argparse
from pathlib import Path

ROD = "94868A713_NO-THREADS_Female-Threaded-Hex-Standoff"
# Chassis millimetres, identified from the 20 mm grid in the marked underside photo.
POSITIONS = {
    ROD: (-60, 80),
    ROD + "-1": (-100, 0),
    ROD + "-2": (100, 0),
    ROD + "-3": (-60, -80),
    ROD + "-4": (60, 80),
    ROD + "-5": (60, -80),
}


def main():
    import FreeCAD as App
    import Part

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    doc = App.openDocument(str(Path("cad/assembly/LeKiwi.FCStd").resolve()))
    joints = {j.Child: j for j in doc.LeKiwiJoints.Group}
    refs = {p.UrdfLink: p for p in doc.LeKiwiReferenceParts.Group}
    assert {j for j in joints if "Hex-Standoff" in j} == set(POSITIONS)
    assert len(set(POSITIONS.values())) == 6
    for plate in ("lower", "upper"):
        source = App.openDocument(
            str(Path(f"cad/parts/base_plate_{plate}.FCStd").resolve())
        )
        profile = source.LaserProfile.Shape
        for x, y in POSITIONS.values():
            # Require a real screw hole surrounded by plate, not space outside it.
            circle = Part.Face(Part.Wire([Part.makeCircle(1.65, App.Vector(x, y, 0))]))
            assert profile.common(circle).Area < 1e-5, (plate, x, y, "hole obstructed")
            assert any(
                abs(Part.Face(w).CenterOfMass.x - x) < 0.001
                and abs(Part.Face(w).CenterOfMass.y - y) < 0.001
                and 3.3 < w.BoundBox.XLength < 3.6
                for w in profile.Wires
            ), (plate, x, y, "missing mounting hole")
    print("PASS: six distinct rod locations match holes in both plates", flush=True)
    upper = joints["base_plate_layer2-v3"]
    assert upper.Parent == ROD
    old_rod = list(map(float, joints[ROD].OriginXYZ.split()))
    old_upper = list(map(float, upper.OriginXYZ.split()))
    # Rod frames are flipped about X. Preserve the upper plate and every child.
    assert joints[ROD].OriginRPY.startswith("3.141592653589793")
    old_upper_world = [
        old_rod[0] + old_upper[0],
        old_rod[1] - old_upper[1],
        old_rod[2] - old_upper[2],
    ]
    if args.apply:
        for name, (x, y) in POSITIONS.items():
            joint = joints[name]
            z = float(joint.OriginXYZ.split()[2])
            joint.OriginXYZ = f"{x / 1000:.9g} {y / 1000:.9g} {z:.9g}"
            world = doc.getObject(refs[name].ReferenceObject)
            placement = world.Placement
            delta = (
                App.Vector(x, y, world.Shape.BoundBox.Center.z)
                - world.Shape.BoundBox.Center
            )
            placement.Base += delta
            world.Placement = placement
        x, y = POSITIONS[ROD]
        upper.OriginXYZ = f"{old_upper_world[0] - x / 1000:.9g} {y / 1000 - old_upper_world[1]:.9g} {old_rod[2] - old_upper_world[2]:.9g}"
        doc.recompute()
    for name, (x, y) in POSITIONS.items():
        world = doc.getObject(refs[name].ReferenceObject)
        centre = world.Shape.BoundBox.Center
        assert abs(centre.x - x) < 0.001 and abs(centre.y - y) < 0.001, (
            name,
            "visible rod placement",
        )
        xyz = list(map(float, joints[name].OriginXYZ.split()))
        assert abs(xyz[0] * 1000 - x) < 0.001 and abs(xyz[1] * 1000 - y) < 0.001, (
            name,
            "joint placement",
        )
    rod_xyz = list(map(float, joints[ROD].OriginXYZ.split()))
    upper_xyz = list(map(float, upper.OriginXYZ.split()))
    new_upper_world = [
        rod_xyz[0] + upper_xyz[0],
        rod_xyz[1] - upper_xyz[1],
        rod_xyz[2] - upper_xyz[2],
    ]
    assert max(abs(a - b) for a, b in zip(old_upper_world, new_upper_world)) < 1e-9
    assert max(abs(a - b) for a, b in zip(new_upper_world, [0, 0, 0.05])) < 1e-9
    if args.apply:
        doc.save()
    print(
        "PASS: six CAD rods and joint poses agree; upper plate remains at (0, 0, 50) mm"
    )


if __name__ == "__main__":
    main()
