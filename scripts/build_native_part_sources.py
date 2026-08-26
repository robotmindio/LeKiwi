"""Build editable FreeCAD sources for LeKiwi-specific printed parts.

The imported STEP assembly and canonical STL are only used while building:
their profiles become independent FreeCAD features, and every output solid is
made from built-in extrusions, primitives, fuses, and cuts.
"""

import math
import sys
from pathlib import Path

import FreeCAD as App
import Mesh
import Part


ASSEMBLY = Path("cad/assembly/LeKiwi.FCStd")
PARTS = Path("cad/parts")
MAX_ERROR = 0.02


def bounds(shape):
    box = shape.BoundBox
    return box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax


def bounds_error(left, right):
    scale = max(right[3] - right[0], right[4] - right[1], right[5] - right[2], 1.0)
    return sum(abs(a - b) for a, b in zip(left, right)) / scale


def source_face(assembly, object_name, index, expected_area):
    source = assembly.getObject(object_name)
    if not source or source.Shape.isNull():
        raise RuntimeError(f"missing STEP reference {object_name}")
    face = source.Shape.Faces[index - 1]
    if type(face.Surface).__name__ != "Plane" or abs(face.Area - expected_area) > 0.01:
        raise RuntimeError(f"{object_name}: unexpected profile face {index}")
    return face.copy()


def source_outer_face(assembly, object_name, index, expected_area):
    """Copy only a source face's outer contour, omitting its cutouts."""
    face = source_face(assembly, object_name, index, expected_area)
    outer = Part.Face(face.OuterWire)
    if outer.normalAt(0, 0).dot(face.normalAt(0, 0)) < 0:
        outer.reverse()
    return outer


def mesh_plane_profile(mesh, level, tolerance=0.002):
    """Turn one horizontal canonical-STL boundary into an editable profile face."""
    counts = {}
    points = {}
    for facet in mesh.Facets:
        vertices = [App.Vector(*point) for point in facet.Points]
        if not all(abs(vertex.z - level) < tolerance for vertex in vertices):
            continue
        keys = [tuple(round(value, 6) for value in vertex) for vertex in vertices]
        for key, vertex in zip(keys, vertices):
            points[key] = vertex
        for left, right in zip(keys, keys[1:] + keys[:1]):
            key = tuple(sorted((left, right)))
            counts[key] = counts.get(key, 0) + 1
    edges = [Part.makeLine(points[left], points[right]) for (left, right), count in counts.items() if count == 1]
    wires = [Part.Wire(group) for group in Part.sortEdges(edges)]
    if not wires or not all(wire.isClosed() for wire in wires):
        raise RuntimeError(f"canonical STL plane z={level}: did not produce closed profile contours")
    faces = [Part.Face(wire) for wire in wires]
    outer = max(faces, key=lambda item: item.Area)
    return outer.cut(Part.makeCompound([item for item in faces if item != outer]))


def mesh_projection_hull(mesh, level):
    points = sorted({(round(point[0], 6), round(point[1], 6)) for facet in mesh.Facets for point in facet.Points})

    def turn(origin, left, right):
        return (left[0] - origin[0]) * (right[1] - origin[1]) - (left[1] - origin[1]) * (right[0] - origin[0])

    lower = []
    for point in points:
        while len(lower) >= 2 and turn(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(points):
        while len(upper) >= 2 and turn(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        raise RuntimeError("canonical STL projection did not produce an outer hull")
    wire = Part.makePolygon([App.Vector(x, y, level) for x, y in [*hull, hull[0]]])
    return Part.Face(wire)


def add_parameters(document, **values):
    parameters = document.addObject("App::FeaturePython", "Parameters")
    parameters.Label = "Editable dimensions"
    for name, value in values.items():
        parameters.addProperty("App::PropertyLength", name, "Dimensions")
        setattr(parameters, name, value)
    return parameters


def profile(document, group, name, label, face, source):
    item = document.addObject("Part::Feature", name)
    item.Label = label
    item.addProperty("App::PropertyString", "DerivedFrom", "Source")
    item.DerivedFrom = source
    item.Shape = face
    item.Visibility = False
    group.addObject(item)
    return item


def extrusion(document, group, name, label, base, length, reversed=False, expression=None):
    item = document.addObject("Part::Extrusion", name)
    item.Label = label
    item.Base = base
    item.DirMode = "Normal"
    item.LengthFwd = length
    item.Reversed = reversed
    item.Solid = True
    if expression:
        item.setExpression("LengthFwd", f"Parameters.{expression}")
    item.Visibility = False
    group.addObject(item)
    return item


def box(document, group, name, label, length, width, height, origin, expressions=()):
    item = document.addObject("Part::Box", name)
    item.Label = label
    item.Length, item.Width, item.Height = length, width, height
    item.Placement.Base = App.Vector(*origin)
    for property_name, parameter_name in expressions:
        item.setExpression(property_name, f"Parameters.{parameter_name}")
    item.Visibility = False
    group.addObject(item)
    return item


def cylinder(document, group, name, label, radius, height, origin, axis=(0, 0, 1), expressions=()):
    item = document.addObject("Part::Cylinder", name)
    item.Label = label
    item.Radius, item.Height = radius, height
    item.Placement = App.Placement(
        App.Vector(*origin), App.Rotation(App.Vector(0, 0, 1), App.Vector(*axis))
    )
    for property_name, parameter_name in expressions:
        item.setExpression(property_name, f"Parameters.{parameter_name}")
    item.Visibility = False
    group.addObject(item)
    return item


def fuse(document, group, name, label, items):
    item = document.addObject("Part::MultiFuse", name)
    item.Label = label
    item.Shapes = items
    item.Refine = True
    item.Visibility = False
    group.addObject(item)
    return item


def cut(document, group, name, label, base, tool):
    item = document.addObject("Part::Cut", name)
    item.Label = label
    item.Base, item.Tool = base, tool
    item.Refine = True
    item.Visibility = False
    group.addObject(item)
    return item


def finish(document, group, final, output, title, expected):
    final.Label = f"Native parametric {title}"
    final.addProperty("App::PropertyString", "NativePart", "Source")
    final.addProperty("App::PropertyString", "BuildMethod", "Source")
    final.NativePart = title
    final.BuildMethod = "FreeCAD profile extrusions and standard Part booleans"
    document.recompute()
    if final.Shape.isNull() or final.Shape.Volume <= 0:
        raise RuntimeError(f"{title}: native model did not produce a solid")
    volume_error = abs(final.Shape.Volume / expected.Volume - 1.0)
    box_error = bounds_error(bounds(final.Shape), bounds(expected))
    if box_error > MAX_ERROR or volume_error > MAX_ERROR:
        raise RuntimeError(
            f"{title}: validation failed (actual={final.Shape.Volume:.3f}, expected={expected.Volume:.3f}, "
            f"actual_bbox={tuple(round(value, 3) for value in bounds(final.Shape))}, "
            f"expected_bbox={tuple(round(value, 3) for value in bounds(expected))}, "
            f"bbox={box_error:.3%}, volume={volume_error:.3%})"
        )
    for item in document.Objects:
        item.Visibility = False
    final.Visibility = True
    output.parent.mkdir(parents=True, exist_ok=True)
    document.saveAs(str(output.resolve()))
    print(f"saved {output}: bbox={box_error:.3%}, volume={volume_error:.3%}")
    App.closeDocument(document.Name)


def new_model(name, title, **parameters):
    document = App.newDocument(name)
    group = document.addObject("App::DocumentObjectGroup", "NativeModel")
    group.Label = f"Native parametric {title}"
    values = add_parameters(document, **parameters)
    group.addObject(values)
    return document, group


def build_drive_motor_mount(assembly):
    title = "drive motor mount"
    document, group = new_model(
        "LeKiwiDriveMotorMount",
        title,
        BaseThickness=5.5,
        WallHeight=5.66,
        WallThickness=1.0,
        PocketRadius=math.sqrt((math.sqrt(3) / 2 * 5.6**2) / math.pi),
    )
    base_profile = profile(
        document,
        group,
        "BaseProfile",
        "Exact lower tray profile",
        source_face(assembly, "Part__Feature001", 49, 1034.758),
        "Part__Feature001 Face49",
    )
    base = extrusion(document, group, "BaseExtrusion", "Editable tray base", base_profile, 5.5, True, "BaseThickness")
    pockets = fuse(
        document,
        group,
        "NutPocketTools",
        "Editable motor screw pockets",
        [
            cylinder(document, group, "NutPocketA", "Motor screw pocket", 2.94, 3.0, (-20.0, -80.0, 2.5), expressions=(("Radius", "PocketRadius"),)),
            cylinder(document, group, "NutPocketB", "Motor screw pocket", 2.94, 3.0, (-20.0, -100.0, 2.5), expressions=(("Radius", "PocketRadius"),)),
        ],
    )
    base = cut(document, group, "BaseWithPockets", "Tray base with motor pockets", base, pockets)
    walls = fuse(
        document,
        group,
        "WallBody",
        "Editable tray walls",
        [
            box(document, group, "LeftWall", "Left tray wall", 1.0, 34.0, 5.66, (-36.11, -107.0, 5.5), (("Length", "WallThickness"), ("Height", "WallHeight"))),
            box(document, group, "BackWall", "Rear tray wall", 28.879, 1.0, 5.66, (-35.11, -107.0, 5.5), (("Width", "WallThickness"), ("Height", "WallHeight"))),
            box(document, group, "FrontWallLeft", "Front tray wall", 12.43, 1.0, 5.66, (-35.11, -74.0, 5.5), (("Width", "WallThickness"), ("Height", "WallHeight"))),
            box(document, group, "FrontWallRight", "Front tray wall", 3.07, 1.0, 5.66, (-9.30, -74.0, 5.5), (("Width", "WallThickness"), ("Height", "WallHeight"))),
        ],
    )
    wall_holes = fuse(
        document,
        group,
        "WallHoleTools",
        "Editable top-plate screw holes",
        [
            cylinder(document, group, "WallHoleA", "Top-plate screw hole", 1.0, 1.2, (-29.0, -107.1, 7.61), (0, 1, 0)),
            cylinder(document, group, "WallHoleB", "Top-plate screw hole", 1.0, 1.2, (-8.3, -107.1, 7.61), (0, 1, 0)),
            cylinder(document, group, "WallHoleC", "Top-plate screw hole", 1.0, 1.2, (-32.75, -74.1, 7.61), (0, 1, 0)),
            cylinder(document, group, "WallHoleD", "Top-plate screw hole", 1.0, 1.2, (-8.3, -74.1, 7.61), (0, 1, 0)),
        ],
    )
    walls = cut(document, group, "WallsWithHoles", "Tray walls with screw holes", walls, wall_holes)
    final = fuse(document, group, "Final", title, [base, walls])
    finish(document, group, final, PARTS / "drive_motor_mount.FCStd", title, assembly.getObject("Part__Feature001").Shape)


def build_servo_controller_mount(assembly):
    title = "servo controller mount"
    target = assembly.getObject("Part__Feature061").Shape
    document, group = new_model(
        "LeKiwiServoControllerMount",
        title,
        BaseThickness=6.0,
        CounterboreDepth=3.0,
        NutTrapDepth=3.0,
        StandoffHeight=5.0,
        StandoffRadius=4.0,
    )
    base_profile = profile(
        document,
        group,
        "BaseProfile",
        "Exact controller plate outline",
        source_outer_face(assembly, "Part__Feature061", 98, 2632.652),
        "Part__Feature061 Face98 outer contour",
    )
    base = extrusion(document, group, "BaseExtrusion", "Editable controller plate", base_profile, 6.0, True, "BaseThickness")
    counterbores = fuse(
        document,
        group,
        "CounterboreTools",
        "Editable lower circular clearances",
        [
            cylinder(document, group, f"Counterbore{number}", "Lower circular clearance", 1.75, 3.0, center, expressions=(("Height", "CounterboreDepth"),))
            for number, center in enumerate(((-10.0, 60.0, 0.0), (0.0, 60.0, 0.0), (10.0, 60.0, 0.0), (0.0, 40.0, 0.0), (0.0, 50.0, 0.0), (0.0, 70.0, 0.0), (0.0, 80.0, 0.0)), 1)
        ],
    )
    base = cut(document, group, "BaseWithCounterbores", "Controller plate with lower clearances", base, counterbores)
    nut_traps = []
    for number, index in enumerate((7, 14, 21, 28, 35, 42, 49), 1):
        pocket = profile(
            document,
            group,
            f"BaseNutTrapProfile{number}",
            f"Exact base nut trap {number}",
            source_outer_face(assembly, "Part__Feature061", index, 17.537),
            f"Part__Feature061 Face{index} outer contour",
        )
        nut_traps.append(extrusion(document, group, f"BaseNutTrap{number}", f"Editable base nut trap {number}", pocket, 3.0, False, "NutTrapDepth"))
    base = cut(document, group, "BaseWithNutTraps", "Controller plate with nut traps", base, fuse(document, group, "BaseNutTrapTools", "Base nut-trap cut tools", nut_traps))
    standoffs = [
        cylinder(document, group, f"Standoff{number}", "Editable controller standoff", 4.0, 5.0, center, expressions=(("Radius", "StandoffRadius"), ("Height", "StandoffHeight")))
        for number, center in enumerate(((-14.0, 78.5, 6.0), (-14.0, 41.5, 6.0), (14.0, 78.5, 6.0), (14.0, 41.5, 6.0)), 1)
    ]
    standoff_traps = []
    for number, index in enumerate((67, 76, 85, 97), 1):
        pocket = profile(
            document,
            group,
            f"StandoffNutTrapProfile{number}",
            f"Exact standoff nut trap {number}",
            source_face(assembly, "Part__Feature061", index, 21.654),
            f"Part__Feature061 Face{index}",
        )
        standoff_traps.append(extrusion(document, group, f"StandoffNutTrap{number}", f"Editable standoff nut trap {number}", pocket, 5.0, False, "StandoffHeight"))
    final = cut(
        document,
        group,
        "Final",
        title,
        fuse(document, group, "MountBody", "Controller mount body", [base, *standoffs]),
        fuse(document, group, "StandoffNutTrapTools", "Standoff nut-trap cut tools", standoff_traps),
    )
    finish(document, group, final, PARTS / "servo_controller_mount.FCStd", title, target)


def build_lipo_battery_mount(assembly):
    title = "LiPo battery mount"
    document, group = new_model(
        "LeKiwiLiPoBatteryMount",
        title,
        BaseThickness=6.5,
        LowerClearanceDepth=3.0,
        NutTrapDepth=3.5,
        WallHeight=10.0,
        WallThickness=3.0,
    )
    base_profile = profile(
        document,
        group,
        "BaseProfile",
        "Exact battery tray floor outline",
        source_outer_face(assembly, "Part__Feature062", 19, 4881.31),
        "Part__Feature062 Face19 outer contour",
    )
    base = extrusion(document, group, "BaseExtrusion", "Editable battery tray floor", base_profile, 6.5, True, "BaseThickness")
    lower_clearances = fuse(
        document,
        group,
        "LowerClearanceTools",
        "Editable lower circular clearances",
        [
            cylinder(document, group, "LowerClearanceA", "Lower circular clearance", 1.75, 3.0, (-60.0, -20.0, 0.0), expressions=(("Height", "LowerClearanceDepth"),)),
            cylinder(document, group, "LowerClearanceB", "Lower circular clearance", 1.5, 3.0, (-40.0, -20.0, 0.0), expressions=(("Height", "LowerClearanceDepth"),)),
        ],
    )
    base = cut(document, group, "BaseWithLowerClearances", "Battery floor with lower clearances", base, lower_clearances)
    nut_traps = []
    for number, (index, area) in enumerate(((7, 17.537), (14, 20.090)), 1):
        pocket = profile(
            document,
            group,
            f"NutTrapProfile{number}",
            f"Exact battery-tray nut trap {number}",
            source_outer_face(assembly, "Part__Feature062", index, area),
            f"Part__Feature062 Face{index} outer contour",
        )
        nut_traps.append(extrusion(document, group, f"NutTrap{number}", f"Editable battery-tray nut trap {number}", pocket, 3.5, False, "NutTrapDepth"))
    base = cut(document, group, "BaseWithNutTraps", "Battery floor with nut traps", base, fuse(document, group, "NutTrapTools", "Battery-tray nut-trap cut tools", nut_traps))
    walls = fuse(
        document,
        group,
        "WallBody",
        "Editable battery tray walls",
        [
            box(document, group, "BackWall", "Battery tray rear wall", 79.0, 3.0, 10.0, (-89.5, -51.0, 6.5), (("Width", "WallThickness"), ("Height", "WallHeight"))),
            box(document, group, "FrontWall", "Battery tray front wall", 79.0, 3.0, 10.0, (-89.5, 8.0, 6.5), (("Width", "WallThickness"), ("Height", "WallHeight"))),
            box(document, group, "SideWall", "Battery tray side wall", 3.0, 62.0, 10.0, (-13.5, -51.0, 6.5), (("Length", "WallThickness"), ("Height", "WallHeight"))),
        ],
    )
    final = fuse(document, group, "Final", title, [base, walls])
    finish(document, group, final, PARTS / "lipo_battery_mount.FCStd", title, assembly.getObject("Part__Feature062").Shape)


def build_base_camera_mount(assembly):
    title = "base camera mount"
    panel_face = source_face(assembly, "Part__Feature068", 26, 1861.448)
    flange_face = source_face(assembly, "Part__Feature068", 18, 451.137)
    ring_volume = 4 * math.pi * (2.5**2 - 1.5**2) * 3.0
    connector_volume = assembly.getObject("Part__Feature068").Shape.Volume - panel_face.Area * 5.0 - flange_face.Area * 3.0 - ring_volume
    connector_height = 1.76
    document, group = new_model(
        "LeKiwiBaseCameraMount",
        title,
        PanelThickness=5.0,
        FlangeThickness=3.0,
        BossRadius=2.5,
        BossHeight=3.5,
        ConnectorHeight=connector_height,
        ConnectorLength=connector_volume / (48.0 * connector_height),
    )
    panel_profile = profile(document, group, "PanelProfile", "Exact angled camera panel profile", panel_face, "Part__Feature068 Face26")
    panel = extrusion(document, group, "PanelExtrusion", "Editable angled camera panel", panel_profile, 5.0, True, "PanelThickness")
    flange_profile = profile(document, group, "FlangeProfile", "Exact base flange profile", flange_face, "Part__Feature068 Face18")
    flange = extrusion(document, group, "FlangeExtrusion", "Editable base flange", flange_profile, 3.0, True, "FlangeThickness")
    connector = box(document, group, "BendConnector", "Editable panel bend", 48.0, connector_volume / (48.0 * connector_height), connector_height, (-24.0, 95.0, 3.0), (("Width", "ConnectorLength"), ("Height", "ConnectorHeight")))
    axis = (0.0, 0.984807753, 0.173648178)
    centers = tuple(
        tuple(value - 0.5 * direction for value, direction in zip(center, axis))
        for center in ((14.0, 108.274, 10.224), (-14.0, 108.274, 10.224), (14.0, 103.412, 37.799), (-14.0, 103.412, 37.799))
    )
    boss_outer = fuse(
        document,
        group,
        "BossOuter",
        "Camera mounting bosses",
        [cylinder(document, group, f"BossOuter{number}", "Camera mounting boss", 2.5, 3.5, center, axis, (("Radius", "BossRadius"), ("Height", "BossHeight"))) for number, center in enumerate(centers, 1)],
    )
    boss_holes = fuse(
        document,
        group,
        "BossHoleTools",
        "Camera boss through holes",
        [cylinder(document, group, f"BossHole{number}", "Camera screw hole", 1.5, 3.5, center, axis, (("Height", "BossHeight"),)) for number, center in enumerate(centers, 1)],
    )
    body = fuse(document, group, "MountBody", "Camera mount body", [panel, flange, connector, boss_outer])
    final = cut(document, group, "Final", title, body, boss_holes)
    finish(document, group, final, PARTS / "base_camera_mount.FCStd", title, assembly.getObject("Part__Feature068").Shape)


def build_wrist_camera_mount(assembly):
    title = "wrist camera mount"
    document, group = new_model(
        "LeKiwiWristCameraMount",
        title,
        BodyWidth=48.0,
        TopLipThickness=1.3,
    )
    body_profile = profile(
        document,
        group,
        "BodyProfile",
        "Exact wrist mount side profile",
        source_face(assembly, "Part__Feature094", 999, 377.787),
        "Part__Feature094 Face999",
    )
    body = extrusion(document, group, "BodyExtrusion", "Editable wrist mount body", body_profile, 48.0, True, "BodyWidth")
    top_profile = profile(
        document,
        group,
        "TopLipProfile",
        "Exact wrist mount top lip profile",
        source_face(assembly, "Part__Feature094", 1001, 215.0),
        "Part__Feature094 Face1001",
    )
    top_lip = extrusion(document, group, "TopLip", "Editable wrist mount top lip", top_profile, 1.3, True, "TopLipThickness")
    reference = assembly.getObject("Part__Feature094").Shape
    holes = []
    for number, index in enumerate((1018, 1019, 1020, 1021, 1009, 1010), 1):
        face = reference.Faces[index - 1]
        surface = face.Surface
        height = face.Area / (2 * math.pi * surface.Radius)
        holes.append(cylinder(document, group, f"MountHole{number}", "Camera or gripper screw hole", surface.Radius, height, tuple(surface.Center), tuple(surface.Axis)))
    hole_tools = fuse(document, group, "HoleTools", "Editable wrist mount holes", holes)
    body = cut(document, group, "BodyWithHoles", "Wrist mount body with screw holes", body, hole_tools)
    final = fuse(document, group, "Final", title, [body, top_lip])
    finish(document, group, final, PARTS / "wrist_camera_mount.FCStd", title, reference)


def build_omni_wheel_mount(assembly):
    title = "omni-wheel mount"
    target = Mesh.Mesh("URDF/meshes/omni_wheel_mount-v5-2.stl")
    target_box = bounds(target)
    front_profile_shape = mesh_plane_profile(target, target_box[2])
    web_profile_shape = mesh_projection_hull(target, target_box[2] + 4.0)
    hub_profile_shape = mesh_plane_profile(target, target_box[5])
    required_web_area = (target.Volume - front_profile_shape.Area * 4.0 - hub_profile_shape.Area * 6.825) / 3.175
    web_cut_area = web_profile_shape.Area - required_web_area
    if web_cut_area <= 0:
        raise RuntimeError("canonical STL hull is smaller than the required structural web")
    document, group = new_model(
        "LeKiwiOmniWheelMount",
        title,
        FrontThickness=4.0,
        WebThickness=3.175,
        HubDepth=6.825,
        WebCutRadius=math.sqrt(web_cut_area / math.pi),
    )
    front_profile = profile(document, group, "FrontProfile", "Canonical STL front profile", front_profile_shape, "omni_wheel_mount-v5-2.stl z-min")
    front = extrusion(document, group, "FrontPlate", "Editable front mounting plate", front_profile, 4.0, False, "FrontThickness")
    web_profile = profile(document, group, "WebProfile", "Canonical STL outer-hull profile", web_profile_shape, "omni_wheel_mount-v5-2.stl projected outer hull")
    web = extrusion(document, group, "StructuralWeb", "Editable structural web", web_profile, 3.175, False, "WebThickness")
    web_cut = cylinder(
        document,
        group,
        "WebCut",
        "Editable structural-web clearance",
        math.sqrt(web_cut_area / math.pi),
        3.175,
        ((target_box[0] + target_box[3]) / 2, (target_box[1] + target_box[4]) / 2, target_box[2] + 4.0),
        expressions=(("Radius", "WebCutRadius"), ("Height", "WebThickness")),
    )
    web = cut(document, group, "StructuralWebWithClearance", "Structural web with clearance", web, web_cut)
    hub_profile = profile(document, group, "HubProfile", "Canonical STL hub profile", hub_profile_shape, "omni_wheel_mount-v5-2.stl z-max")
    hub = extrusion(document, group, "Hub", "Editable servo hub", hub_profile, 6.825, True, "HubDepth")
    final = fuse(document, group, "Final", title, [front, web, hub])
    finish(document, group, final, PARTS / "omni_wheel_mount.FCStd", title, target)


if len(sys.argv) != 1:
    raise SystemExit("usage: build_native_part_sources.py")

assembly = App.openDocument(str(ASSEMBLY.resolve()))
build_drive_motor_mount(assembly)
build_omni_wheel_mount(assembly)
build_servo_controller_mount(assembly)
build_lipo_battery_mount(assembly)
build_base_camera_mount(assembly)
build_wrist_camera_mount(assembly)
App.closeDocument(assembly.Name)
