"""Derive RobotSkin overlays from the editable chassis; run with FreeCADCmd."""

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import FreeCAD as App
import Mesh
import MeshPart
import Part

from scripts.cad_utils import bounds, urdf_matrix
from scripts.replace_arm_with_so101 import joint_pose, replace_arm

OUT = Path("cad/generated/robotskin")
LOWER = "base_plate_layer1-v5"
UPPER = "base_plate_layer2-v3"
NAMES = ("top", "floor", "ceiling")


def rectangle(box, clearance):
    x0, y0, _, x1, y1, _ = box
    points = [
        (x0 - clearance, y0 - clearance),
        (x1 + clearance, y0 - clearance),
        (x1 + clearance, y1 + clearance),
        (x0 - clearance, y1 + clearance),
    ]
    return points


def face(points):
    vertices = [App.Vector(x, y, 0) for x, y in points]
    return Part.Face(Part.makePolygon(vertices + vertices[:1]))


def footprint(solid, z, clearance):
    """Oriented convex footprint of hardware reaching this skin's clearance zone."""
    if solid.BoundBox.ZMin >= z + 4 + clearance or solid.BoundBox.ZMax <= z - clearance:
        return None
    vertices = (
        solid.Topology[0] if hasattr(solid, "Topology") else solid.tessellate(0.02)[0]
    )
    points = sorted(set((round(p.x, 5), round(p.y, 5)) for p in vertices))

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    halves = []
    for ordered in (points, points[::-1]):
        half = []
        for p in ordered:
            while len(half) >= 2 and cross(half[-2], half[-1], p) <= 1e-9:
                half.pop()
            half.append(p)
        halves.extend(half[:-1])
    if clearance == 0:
        return [list(p) for p in halves]
    wire = face(halves).OuterWire.makeOffset2D(clearance, join=2)
    return [[v.Point.x, v.Point.y] for v in wire.OrderedVertexes]


def prepare(clearance, motor_clearance):
    doc = App.openDocument("cad/assembly/LeKiwi.FCStd")
    model = ET.Element("robot")
    links = {item.UrdfName: item for item in doc.LeKiwiLinks.Group}
    # The STEP occurrences are the physical assembly datum. Legacy URDF meshes
    # were recentered independently and do not preserve these mounting positions.
    references = {
        p.UrdfLink: doc.getObject(p.ReferenceObject)
        for p in doc.LeKiwiReferenceParts.Group
        if p.ReferenceObject
    }
    for name in links:
        ET.SubElement(model, "link", name=name)
    for item in doc.LeKiwiJoints.Group:
        joint = ET.SubElement(model, "joint", name=item.UrdfName, type=item.JointType)
        ET.SubElement(joint, "parent", link=item.Parent)
        ET.SubElement(joint, "child", link=item.Child)
        ET.SubElement(joint, "origin", xyz=item.OriginXYZ, rpy=item.OriginRPY)
        ET.SubElement(joint, "axis", xyz=item.Axis)
    parents = {j.find("child").get("link"): j for j in model.findall("joint")}

    def pose(name):
        return (
            App.Matrix()
            if name == LOWER
            else joint_pose(model, parents[name].get("name"), LOWER)
        )

    def shape(name):
        if hasattr(links[name].CadParts[0], "Mesh"):
            assert len(links[name].CadParts) == 1
            result = links[name].CadParts[0].Mesh.copy()
            result.transform(pose(name))
            return result
        result = Part.makeCompound([p.Shape for p in links[name].CadParts])
        result.transformShape(pose(name))
        return result

    bottom, upper = shape(LOWER), shape(UPPER)
    height = upper.BoundBox.ZMin
    assert abs(height - 50) < 0.01, "Revisit overlay layout if chassis spacing changes"
    assert abs(upper.BoundBox.ZLength - 7) < 0.01
    context = App.newDocument("LeKiwiRobotSkin")
    for name, solid in [("LowerPlate", bottom), ("UpperPlate", upper)]:
        item = context.addObject("Part::Feature", name)
        item.Label = LOWER if name == "LowerPlate" else UPPER
        item.Shape = solid
    obstacles = []
    motors, posts, mounts = [], [], []
    for name in links:
        wheel_part = any(
            s in name
            for s in (
                "drive_motor_mount-",
                "ST3215_Servo",
                "omni_wheel_mount-",
                "Omni-Directional-Wheel",
            )
        )
        if not (wheel_part or "Hex-Standoff" in name):
            continue
        solid = shape(name)
        is_mesh = hasattr(solid, "Topology")
        item = context.addObject(
            "Mesh::Feature" if is_mesh else "Part::Feature", "Support"
        )
        item.Label = name
        if is_mesh:
            item.Mesh = solid
        else:
            item.Shape = solid
        box = solid.BoundBox
        if wheel_part:
            motors.append(solid)
            if name.startswith("drive_motor_mount-"):
                assert "v2" in links[name].CadParts[0].LinkedObject.NativePart
                mounts.append((name, solid))
        else:
            obstacles.append(solid)
            # Reserve washer / screw-head access as well as the actual hex post.
            posts.append(
                [
                    box.Center.x,
                    box.Center.y,
                    max(4.0, math.hypot(box.XLength, box.YLength) / 2) + clearance,
                ]
            )
    assert len(motors) == 12 and len(posts) == 6 and len(mounts) == 3

    replace_arm(model)
    # Load the installed SO-101 base, including its fixed servo, from pinned meshes.
    arm_boxes = []
    for link in model.findall("link"):
        name = link.get("name")
        if not name.startswith("so101_"):
            continue
        for visual in link.findall("visual"):
            geometry = visual.find("geometry/mesh")
            mesh = Mesh.Mesh(str(Path("URDF") / geometry.get("filename")))
            scale = list(map(float, geometry.get("scale", "1 1 1").split()))
            matrix = App.Matrix()
            matrix.scale(*(s * 1000 for s in scale))
            mesh.transform(matrix)
            parent_joint = next(
                j for j in model.findall("joint") if j.find("child").get("link") == name
            )
            matrix = joint_pose(model, parent_joint.get("name"), LOWER).multiply(
                urdf_matrix(visual.find("origin"))
            )
            mesh.transform(matrix)
            item = context.addObject("Mesh::Feature", "Arm")
            item.Label = name
            item.Mesh = mesh
            if (
                name == "so101_base_link"
                or mesh.BoundBox.ZMin < upper.BoundBox.ZMax + 4 + clearance
            ):
                arm_boxes.append(rectangle(bounds(mesh), clearance))
    assert arm_boxes, "Missing installed arm footprint"
    # Open the arm recess to the front edge; do not leave a detached narrow cap.
    for polygon in arm_boxes:
        if polygon[2][1] > upper.BoundBox.YMax - 20:
            polygon[2] = (polygon[2][0], upper.BoundBox.YMax + clearance)
            polygon[3] = (polygon[3][0], upper.BoundBox.YMax + clearance)

    # Include the rest of the actual chassis for the requested full-build views.
    present = {p.Label for p in context.Objects}
    for link in model.findall("link"):
        name = link.get("name")
        if name.startswith("so101_") or name in present:
            continue
        if name in references:
            item = context.addObject("Part::Feature", "Component")
            item.Shape = references[name].Shape.copy()
            item.Label = name
        else:
            for part in links[name].CadParts:
                item = context.addObject(
                    "Mesh::Feature" if hasattr(part, "Mesh") else "Part::Feature",
                    "Component",
                )
                item.Label = name
                if hasattr(part, "Mesh"):
                    mesh = part.Mesh.copy()
                    mesh.transform(pose(name))
                    item.Mesh = mesh
                else:
                    item.Shape = shape(name)
    (OUT / "scene").mkdir(exist_ok=True)
    scene = []
    for item in context.Objects:
        mesh = (
            item.Mesh
            if hasattr(item, "Mesh")
            else MeshPart.meshFromShape(
                Shape=item.Shape,
                LinearDeflection=0.05,
                AngularDeflection=0.15,
                Relative=False,
            )
        )
        path = OUT / "scene" / (item.Name + ".stl")
        mesh.write(str(path))
        scene.append({"name": item.Label, "file": "scene/" + path.name})
    (OUT / "scene.json").write_text(json.dumps(scene, indent=2) + "\n")

    data = []
    for name in NAMES:
        source = links[LOWER if name == "floor" else UPPER].CadParts[0].Shape
        horizontal = [f for f in source.Faces if f.BoundBox.ZLength < 1e-5]
        profile = max(horizontal, key=lambda f: f.Area)
        # Laser profiles use straight polygon edges; retain their original perimeter.
        outline = [[v.Point.x, v.Point.y] for v in profile.OuterWire.OrderedVertexes]
        region = Part.Face(face(outline).OuterWire.makeOffset2D(-0.5))
        z = (
            0
            if name == "floor"
            else height - 4
            if name == "ceiling"
            else upper.BoundBox.ZMax
        )
        motor_bases = []
        cuts = [
            polygon
            for solid in motors
            if (polygon := footprint(solid, z, motor_clearance))
        ]
        for mount_name, solid in mounts:
            if (cut := footprint(solid, z, motor_clearance)) is not None:
                motor_bases.append(
                    dict(
                        name=mount_name,
                        footprint=footprint(solid, 0, 0),
                        cut=cut,
                        clearance_mm=motor_clearance,
                    )
                )
        if name == "top":
            cuts += arm_boxes
        for polygon in cuts:
            region = region.cut(face(polygon))
        for x, y, radius in posts:
            # Match OpenSCAD's 32-sided circle, including its intersections at the rim.
            region = region.cut(
                face(
                    [
                        (
                            x + radius * math.cos(i * math.tau / 32),
                            y + radius * math.sin(i * math.tau / 32),
                        )
                        for i in range(32)
                    ]
                )
            )
        assert region.isValid() and len(region.Faces) == 1, (
            name,
            "disconnected overlay",
            len(region.Faces),
            arm_boxes,
        )
        boundary = Part.makeCompound(region.Edges)
        ports = []
        for x in range(-100, 101, 10):
            for y in range(-100, 101, 10):
                point = App.Vector(x, y, 0)
                if (
                    region.isInside(point, 1e-7, True)
                    and boundary.distToShape(Part.Vertex(point))[0] >= 5.5
                ):
                    ports.append([x, y])
        hole_centres = []
        for wire in profile.Wires:
            if 3.3 < wire.BoundBox.XLength < 3.6 and 3.3 < wire.BoundBox.YLength < 3.6:
                centre = Part.Face(wire).CenterOfMass
                if wire.distToShape(Part.Vertex(centre))[0] >= 1.65:
                    hole_centres.append(centre)
        chassis_ports = [
            [x, y]
            for x, y in ports
            if any(abs(p.x - x) < 0.001 and abs(p.y - y) < 0.001 for p in hole_centres)
        ]
        assert len(chassis_ports) >= 4, (
            f"{name}: insufficient chassis-aligned RobotSkin ports"
        )
        blank = region.extrude(App.Vector(0, 0, 4))
        blank.translate(App.Vector(0, 0, z))
        for obstacle in obstacles:
            assert blank.common(obstacle).Volume < 1e-5, f"{name}: support collision"
        # The full convex projections conservatively clear solids and mesh-only wheels.
        for polygon in cuts:
            assert region.common(face(polygon)).Area < 1e-5, (
                f"{name}: hardware projection collision"
            )
        for plate in (bottom, upper):
            assert blank.common(plate).Volume < 1e-5, f"{name}: chassis collision"
        item = context.addObject("Part::Feature", name.title() + "Envelope")
        item.Shape = blank
        data.append(
            dict(
                name=name,
                outline=outline,
                cuts=cuts,
                posts=posts,
                chassis_ports=chassis_ports,
                ports=ports,
                z=z,
                port_count=len(ports),
                motor_bases=motor_bases,
            )
        )
        print(f"{name}: {len(ports)} complete ports, z={z:g}..{z + 4:g} mm")
    context.recompute()
    context.saveAs(str((OUT / "layout.FCStd").resolve()))
    (OUT / "layout.json").write_text(json.dumps(data, indent=2) + "\n")
    # OpenSCAD consumes the same measured regions and validated port centres.
    arrays = [[d[k] for k in ("outline", "cuts", "posts", "ports")] for d in data]
    (OUT / "layout.scad").write_text("layouts = " + json.dumps(arrays) + ";\n")


def finish():
    doc = App.openDocument(str(OUT / "layout.FCStd"))
    data = json.loads((OUT / "layout.json").read_text())
    for entry in data:
        name = entry["name"]
        mesh = Mesh.Mesh(str(OUT / (name + ".stl")))
        assert mesh.isSolid() and mesh.Volume > 0, f"{name}: invalid STL"
        assert mesh.countComponents() == 1, f"{name}: disconnected STL"
        assert abs(mesh.BoundBox.ZLength - 4) < 0.001
        if name == "ceiling":
            # Exposed ports point down; preserve the chassis X/Y coordinates.
            mesh.transform(App.Rotation(App.Vector(1, 0, 0), 180).toMatrix())
            mesh.translate(0, 0, entry["z"] + 4)
        else:
            mesh.translate(0, 0, entry["z"])
        envelope = doc.getObject(name.title() + "Envelope")
        # Print-frame vertices and faces are checked by verify_robotskin_surfaces.py.
        doc.removeObject(envelope.Name)
        item = doc.addObject("Mesh::Feature", name.title() + "RobotSkin")
        item.Mesh = mesh
        mesh.write(str(OUT / (name + "_installed.stl")))
        entry["volume_mm3"] = mesh.Volume
    doc.recompute()
    doc.saveAs(str((OUT / "LeKiwi_RobotSkin.FCStd").resolve()))
    (OUT / "checks.json").write_text(json.dumps(data, indent=2) + "\n")
    print(
        "PASS: three connected solid meshes inside the checked support-clearance envelopes"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finish", action="store_true")
    parser.add_argument("--clearance", type=float, default=1.0)
    parser.add_argument(
        "--motor-clearance",
        type=float,
        default=4.0,
        help="Per-side clearance around the installed v2 wheel assemblies",
    )
    args = parser.parse_args()
    if not math.isfinite(args.clearance) or not 0.5 <= args.clearance <= 3:
        parser.error("--clearance must be between 0.5 and 3 mm")
    if not math.isfinite(args.motor_clearance) or not 0.5 <= args.motor_clearance <= 6:
        parser.error("--motor-clearance must be between 0.5 and 6 mm")
    OUT.mkdir(parents=True, exist_ok=True)
    finish() if args.finish else prepare(args.clearance, args.motor_clearance)
