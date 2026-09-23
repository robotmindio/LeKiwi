"""Install three native v2 cages and reorient their complete wheel units."""

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def main():
    import FreeCAD as App
    import Part
    import Mesh
    from scripts.cad_utils import bounds, bounds_error, urdf_matrix
    from scripts.replace_arm_with_so101 import joint_pose

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    doc = App.openDocument(str(Path("cad/assembly/LeKiwi.FCStd").resolve()))
    links = {p.UrdfName: p for p in doc.LeKiwiLinks.Group}
    joints = {p.Child: p for p in doc.LeKiwiJoints.Group}
    refs = {p.UrdfLink: p for p in doc.LeKiwiReferenceParts.Group}
    source = App.openDocument(str(Path("cad/parts/drive_motor_mount.FCStd").resolve()))
    assert "v2" in source.Final.NativePart
    for x in (11.05, 31.05):
        for z in (3.75, 43.75):
            axis = Part.makeCylinder(
                1.45, 45.5, App.Vector(x, 0, z), App.Vector(0, 1, 0)
            )
            assert source.Final.Shape.common(axis).Volume < 1e-5, (
                "v2 screw passage obstructed"
            )

    def origin(placement):
        yaw, pitch, roll = placement.Rotation.getYawPitchRoll()
        return {
            "xyz": " ".join(f"{v / 1000:.12g}" for v in placement.Base),
            "rpy": " ".join(f"{math.radians(v):.12g}" for v in (roll, pitch, yaw)),
        }

    # STL X is radial depth, Y is installed height, Z is tangential width.
    cage = App.Placement(App.Vector(23.75, -68.95, 0), App.Rotation(-90, 0, 90))
    servo_turn = App.Placement(
        App.Vector(-17.86, -0.5, 10.25), App.Rotation(App.Vector(0, 1, 0), 90)
    )
    expected = {}
    unit_names = []
    for suffix, angle in (("-2", 0), ("-1", 120), ("", -120)):
        mount = "drive_motor_mount-v11" + suffix
        servo = "ST3215_Servo_Motor-v1" + suffix
        spin = App.Placement(App.Vector(), App.Rotation(App.Vector(0, 0, 1), angle))
        world_cage = spin * cage
        raw = doc.getObject(refs[servo].ReferenceObject).Shape
        local = links[servo].CadParts[0].Shape
        physical_pose = raw.Placement * local.Placement.inverse()
        check = local.copy()
        check.Placement = physical_pose * check.Placement
        assert max(abs(a - b) for a, b in zip(bounds(check), bounds(raw))) < 0.05
        world_servo = spin * servo_turn * spin.inverse() * physical_pose
        placed_cage = source.Final.Shape.copy()
        placed_cage.Placement = world_cage * placed_cage.Placement
        placed_servo = local.copy()
        placed_servo.Placement = world_servo * placed_servo.Placement
        overlap = placed_cage.common(placed_servo)
        # The vendor servo corners also intersect the upstream STL (~0.62 mm3).
        # Preserve the supplied cage; report this reference mismatch, not zero interference.
        print(mount, "reference servo/cage overlap mm3:", overlap.Volume, flush=True)
        assert overlap.Volume < 1.0, (
            mount,
            "servo/cage overlap exceeds reference tolerance",
        )
        expected[mount] = origin(world_cage)
        expected[servo] = origin(world_cage.inverse() * world_servo)
        # The four fastening axes must be actual holes in the lower chassis.
        plate = App.openDocument(
            str(Path("cad/parts/base_plate_lower.FCStd").resolve())
        ).LaserProfile.Shape
        for x in (11.05, 31.05):
            for z in (3.75, 43.75):
                point = world_cage.multVec(App.Vector(x, 0, z))
                assert any(
                    (Part.Face(w).CenterOfMass - point).Length < 0.001
                    and 3.3 < w.BoundBox.XLength < 3.6
                    for w in plate.Wires
                ), (mount, point)
        unit_names.extend(
            [
                mount,
                servo,
                "omni_wheel_mount-v5" + suffix,
                "4-Omni-Directional-Wheel_Single_Body-v1" + suffix,
            ]
        )
    if args.apply:
        for child, pose in expected.items():
            joints[child].OriginXYZ = pose["xyz"]
            joints[child].OriginRPY = pose["rpy"]
    for child, pose in expected.items():
        actual = App.Placement(
            urdf_matrix(
                ET.Element(
                    "origin", xyz=joints[child].OriginXYZ, rpy=joints[child].OriginRPY
                )
            )
        )
        target = App.Placement(urdf_matrix(ET.Element("origin", **pose)))
        assert (actual.Base - target.Base).Length < 1e-6 and actual.Rotation.isSame(
            target.Rotation, 1e-8
        ), child

    if args.apply:
        model = ET.Element("robot")
        for j in doc.LeKiwiJoints.Group:
            node = ET.SubElement(model, "joint", name=j.UrdfName)
            ET.SubElement(node, "parent", link=j.Parent)
            ET.SubElement(node, "child", link=j.Child)
            ET.SubElement(node, "origin", xyz=j.OriginXYZ, rpy=j.OriginRPY)
        group = doc.getObject("InstalledWheelUnits") or doc.addObject(
            "App::DocumentObjectGroup", "InstalledWheelUnits"
        )
        group.Label = "Installed v2 motor cages and wheel units"
        for i, name in enumerate(unit_names):
            doc.getObject(refs[name].ReferenceObject).Visibility = False
            node = doc.getObject(f"InstalledWheelPart{i}") or doc.addObject(
                "App::Link", f"InstalledWheelPart{i}"
            )
            node.LinkedObject = links[name].CadParts[0]
            node.LinkTransform = True
            node.Placement = App.Placement(
                joint_pose(model, joints[name].UrdfName, "base_plate_layer1-v5")
            )
            node.Label = name
            node.Visibility = True
            group.addObject(node)
        doc.recompute()
        doc.save()
        Path("cad/wheel_mount_v2_poses.json").write_text(
            json.dumps(expected, indent=2) + "\n"
        )
        mapping_path = Path("cad/reference_mapping.json")
        mapping = json.loads(mapping_path.read_text())
        reference = Mesh.Mesh("3DPrintMeshes/drive_motor_mount_v2.stl")
        for item in mapping:
            if item["urdf_link"].startswith("drive_motor_mount-v11"):
                item.update(
                    mesh_filename="../3DPrintMeshes/drive_motor_mount_v2.stl",
                    visual_xyz="0 0 0",
                    visual_rpy="0 0 0",
                    source_bbox_error=bounds_error(
                        bounds(source.Final.Shape), bounds(reference)
                    ),
                    link_bbox_error=bounds_error(
                        bounds(source.Final.Shape), bounds(reference)
                    ),
                    volume_error=abs(source.Final.Shape.Volume / reference.Volume - 1),
                )
        mapping_path.write_text(json.dumps(mapping, indent=2) + "\n")
    print("PASS: three native v2 cages, 12 chassis fastener axes, and servo poses")


if __name__ == "__main__":
    main()
