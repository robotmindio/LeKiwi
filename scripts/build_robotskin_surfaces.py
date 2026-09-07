"""Derive RobotSkin overlays from the editable chassis; run with FreeCADCmd."""

import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import FreeCAD as App
import Mesh
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


def prepare(clearance):
    doc = App.openDocument("cad/assembly/LeKiwi.FCStd")
    model = ET.Element("robot")
    links = {item.UrdfName: item for item in doc.LeKiwiLinks.Group}
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
        item.Shape = solid
    obstacles = []
    motors, posts = [], []
    for name in links:
        if not (name.startswith("drive_motor_mount-") or "Hex-Standoff" in name):
            continue
        solid = shape(name)
        item = context.addObject("Part::Feature", "Support")
        item.Label = name
        item.Shape = solid
        obstacles.append(solid)
        box = solid.BoundBox
        if name.startswith("drive_motor_mount-"):
            motors.append(rectangle(bounds(solid), clearance))
        else:
            # Reserve washer / screw-head access as well as the actual hex post.
            posts.append(
                [
                    box.Center.x,
                    box.Center.y,
                    max(4.0, math.hypot(box.XLength, box.YLength) / 2) + clearance,
                ]
            )
    assert len(motors) == 3 and len(posts) == 6

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

    data = []
    for name in NAMES:
        source = links[LOWER if name == "floor" else UPPER].CadParts[0].Shape
        horizontal = [f for f in source.Faces if f.BoundBox.ZLength < 1e-5]
        profile = max(horizontal, key=lambda f: f.Area)
        # Laser profiles use straight polygon edges; retain their original perimeter.
        outline = [[v.Point.x, v.Point.y] for v in profile.OuterWire.OrderedVertexes]
        region = Part.Face(face(outline).OuterWire.makeOffset2D(-0.5))
        cuts = motors if name == "floor" else arm_boxes if name == "top" else []
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
        # Four existing chassis grid holes, shared by both upper overlays.
        screws = [[-60, -60], [60, -60], [-80, -20], [80, -20]]
        for x, y in screws:
            point = App.Vector(x, y, 0)
            assert region.isInside(point, 1e-7, True), (
                name,
                "screw outside overlay",
                x,
                y,
            )
            assert region.distToShape(Part.Vertex(point))[0] < 1e-7
            assert boundary.distToShape(Part.Vertex(point))[0] > 4
            # Confirm actual hole in the underlying laser plate, not just grid arithmetic.
            solid = bottom if name == "floor" else upper
            probe = Part.makeCylinder(1.65, 7, App.Vector(x, y, solid.BoundBox.ZMin))
            assert solid.common(probe).Volume < 1e-5, (
                name,
                "missing chassis hole",
                x,
                y,
            )
        ports = []
        for x in range(-105, 106, 10):
            for y in range(-105, 106, 10):
                point = App.Vector(x, y, 0)
                if (
                    region.isInside(point, 1e-7, True)
                    and boundary.distToShape(Part.Vertex(point))[0] >= 5.5
                    and all(math.hypot(x - sx, y - sy) >= 9 for sx, sy in screws)
                ):
                    ports.append([x, y])
        z = (
            0
            if name == "floor"
            else height - 4
            if name == "ceiling"
            else upper.BoundBox.ZMax
        )
        blank = region.extrude(App.Vector(0, 0, 4))
        blank.translate(App.Vector(0, 0, z))
        for obstacle in obstacles:
            assert blank.common(obstacle).Volume < 1e-5, f"{name}: support collision"
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
                screws=screws,
                ports=ports,
                z=z,
                port_count=len(ports),
            )
        )
        print(f"{name}: {len(ports)} complete ports, z={z:g}..{z + 4:g} mm")
    context.recompute()
    context.saveAs(str((OUT / "layout.FCStd").resolve()))
    (OUT / "layout.json").write_text(json.dumps(data, indent=2) + "\n")
    # OpenSCAD consumes the same measured regions and validated port centres.
    arrays = [
        [d[k] for k in ("outline", "cuts", "posts", "screws", "ports")] for d in data
    ]
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
    args = parser.parse_args()
    if not math.isfinite(args.clearance) or not 0.5 <= args.clearance <= 3:
        parser.error("--clearance must be between 0.5 and 3 mm")
    OUT.mkdir(parents=True, exist_ok=True)
    finish() if args.finish else prepare(args.clearance)
