"""Build editable FreeCAD sources for LeKiwi-specific printed parts.

The imported STEP assembly and canonical STL are only used while building:
their profiles become independent FreeCAD features, and every output solid is
made from built-in extrusions, primitives, fuses, and cuts.
"""

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


def source_cylinder_face(assembly, object_name, index, expected_area):
    source = assembly.getObject(object_name)
    if not source or source.Shape.isNull():
        raise RuntimeError(f"missing STEP reference {object_name}")
    face = source.Shape.Faces[index - 1]
    if type(face.Surface).__name__ != "Cylinder" or abs(face.Area - expected_area) > 0.01:
        raise RuntimeError(f"{object_name}: unexpected cylindrical face {index}")
    return face.copy()


def mesh_slice_profile(mesh, level, start=None):
    """Turn one horizontal canonical-STL slice into an editable profile face."""
    edges = {}
    for facet in mesh.Facets:
        vertices = [App.Vector(*point) for point in facet.Points]
        hits = []
        for left, right in zip(vertices, vertices[1:] + vertices[:1]):
            left_distance, right_distance = left.z - level, right.z - level
            if left_distance * right_distance < 0:
                hits.append(left + (right - left) * (-left_distance / (right_distance - left_distance)))
        keys = []
        for point in hits:
            key = tuple(round(value, 6) for value in point)
            if key not in keys:
                keys.append(key)
        if len(keys) == 2 and keys[0] != keys[1]:
            edges[tuple(sorted(keys))] = keys
    wires = [Part.Wire(group) for group in Part.sortEdges([Part.makeLine(App.Vector(*left), App.Vector(*right)) for left, right in edges.values()])]
    if not wires or not all(wire.isClosed() for wire in wires):
        raise RuntimeError(f"canonical STL slice z={level}: did not produce closed profile contours")
    faces = sorted((Part.Face(wire) for wire in wires), key=lambda item: item.Area, reverse=True)
    result = faces[0]
    for index, face in enumerate(faces[1:], 1):
        # Nested contours alternate between material and void in a mesh slice.
        depth = sum(parent.common(face).Area >= face.Area - 0.001 for parent in faces[:index])
        result = result.fuse(face) if depth % 2 == 0 else result.cut(face)
    normalized = []
    for face in result.Faces:
        face = face.copy()
        if face.normalAt(0, 0).z < 0:
            face.reverse()
        normalized.append(face)
    result = normalized[0] if len(normalized) == 1 else Part.makeCompound(normalized)
    if start is not None:
        result.translate(App.Vector(0, 0, start - level))
    return result


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


def cylinder_from_source_face(document, group, name, label, face, expressions=()):
    surface = face.Surface
    if type(surface).__name__ != "Cylinder" or not face.Vertexes:
        raise RuntimeError(f"{name}: expected a finite cylindrical source face")
    distances = [(vertex.Point - surface.Center).dot(surface.Axis) for vertex in face.Vertexes]
    origin = surface.Center + surface.Axis * min(distances)
    return cylinder(
        document,
        group,
        name,
        label,
        surface.Radius,
        max(distances) - min(distances),
        tuple(origin),
        tuple(surface.Axis),
        expressions,
    )


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
        WallThickness=1.0,
        LowerClearanceDepth=2.5,
        NutTrapDepth=3.0,
    )
    base_profile = profile(
        document,
        group,
        "BaseProfile",
        "Exact lower tray outline",
        source_outer_face(assembly, "Part__Feature001", 49, 1034.758),
        "Part__Feature001 Face49 outer contour",
    )
    base = extrusion(document, group, "BaseExtrusion", "Editable tray base", base_profile, 5.5, True, "BaseThickness")
    lower_clearances = fuse(
        document,
        group,
        "LowerClearanceTools",
        "Editable lower circular clearances",
        [
            cylinder(document, group, "LowerClearanceA", "Lower circular clearance", 1.75, 2.5, (-20.0, -80.0, 0.0), expressions=(("Height", "LowerClearanceDepth"),)),
            cylinder(document, group, "LowerClearanceB", "Lower circular clearance", 1.75, 2.5, (-20.0, -100.0, 0.0), expressions=(("Height", "LowerClearanceDepth"),)),
        ],
    )
    base = cut(document, group, "BaseWithLowerClearances", "Tray base with lower clearances", base, lower_clearances)
    nut_traps = []
    for number, index in enumerate((7, 14), 1):
        pocket = profile(
            document,
            group,
            f"NutTrapProfile{number}",
            f"Exact motor nut trap {number}",
            source_outer_face(assembly, "Part__Feature001", index, 17.537),
            f"Part__Feature001 Face{index} outer contour",
        )
        nut_traps.append(extrusion(document, group, f"NutTrap{number}", f"Editable motor nut trap {number}", pocket, 3.0, False, "NutTrapDepth"))
    base = cut(document, group, "BaseWithNutTraps", "Tray base with motor nut traps", base, fuse(document, group, "NutTrapTools", "Motor nut-trap cut tools", nut_traps))
    walls = []
    for number, (index, area, label) in enumerate(
        ((19, 271.235, "Front"), (20, 379.440, "Left"), (21, 320.826, "Rear")),
        1,
    ):
        wall_profile = profile(
            document,
            group,
            f"{label}WallProfile",
            f"Exact {label.lower()} tray-wall profile",
            source_face(assembly, "Part__Feature001", index, area),
            f"Part__Feature001 Face{index}",
        )
        walls.append(extrusion(document, group, f"{label}Wall", f"Editable {label.lower()} tray wall", wall_profile, 1.0, True, "WallThickness"))
    final = fuse(document, group, "Final", title, [base, *walls])
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
    document, group = new_model(
        "LeKiwiBaseCameraMount",
        title,
        BodyWidth=48.0,
        ConnectorClearanceWidth=8.5,
        LowerClearanceRadius=1.75,
        LowerClearanceDepth=3.0,
        BossRadius=2.5,
        BossDepth=3.0,
        BossHoleRadius=1.5,
        BossHoleLength=8.0,
    )
    body_profile = profile(
        document,
        group,
        "BodyProfile",
        "Exact camera-mount side profile",
        source_face(assembly, "Part__Feature068", 17, 251.491),
        "Part__Feature068 Face17",
    )
    body = extrusion(document, group, "BodyExtrusion", "Editable camera-mount body", body_profile, 48.0, True, "BodyWidth")
    connector_profile = profile(
        document,
        group,
        "ConnectorClearanceProfile",
        "Exact camera-connector clearance profile",
        source_face(assembly, "Part__Feature068", 9, 22.5),
        "Part__Feature068 Face9",
    )
    connector_clearance = extrusion(
        document,
        group,
        "ConnectorClearance",
        "Editable camera-connector clearance",
        connector_profile,
        8.5,
        False,
        "ConnectorClearanceWidth",
    )
    lower_clearances = [
        cylinder_from_source_face(
            document,
            group,
            f"LowerClearance{number}",
            "Lower circular clearance",
            source_cylinder_face(assembly, "Part__Feature068", index, 32.987),
            (("Radius", "LowerClearanceRadius"), ("Height", "LowerClearanceDepth")),
        )
        for number, index in enumerate((19, 20, 21), 1)
    ]
    body = cut(
        document,
        group,
        "BodyWithClearances",
        "Camera mount body with lower clearances",
        body,
        fuse(document, group, "LowerClearanceTools", "Camera-mount clearance tools", [connector_clearance, *lower_clearances]),
    )
    bosses = [
        cylinder_from_source_face(
            document,
            group,
            f"Boss{number}",
            "Editable camera mounting boss",
            source_cylinder_face(assembly, "Part__Feature068", index, 47.124),
            (("Radius", "BossRadius"), ("Height", "BossDepth")),
        )
        for number, index in enumerate((1, 3, 5, 7), 1)
    ]
    boss_holes = [
        cylinder_from_source_face(
            document,
            group,
            f"BossHole{number}",
            "Camera boss through hole",
            source_cylinder_face(assembly, "Part__Feature068", index, 75.398),
            (("Radius", "BossHoleRadius"), ("Height", "BossHoleLength")),
        )
        for number, index in enumerate((27, 28, 29, 30), 1)
    ]
    final = cut(
        document,
        group,
        "Final",
        title,
        fuse(document, group, "MountBody", "Camera mount body", [body, *bosses]),
        fuse(document, group, "BossHoleTools", "Camera boss through-hole tools", boss_holes),
    )
    finish(document, group, final, PARTS / "base_camera_mount.FCStd", title, assembly.getObject("Part__Feature068").Shape)


def build_wrist_camera_mount(assembly):
    title = "wrist camera mount"
    reference = assembly.getObject("Part__Feature094").Shape
    document, group = new_model(
        "LeKiwiWristCameraMount",
        title,
        BodyWidth=48.0,
        CameraPlateThickness=5.0,
        BossRadius=2.5,
        BossDepth=3.0,
        BossHoleRadius=1.5,
        BossHoleLength=8.0,
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
    plate_profile = profile(
        document,
        group,
        "CameraPlateProfile",
        "Exact angled camera-plate profile",
        source_face(assembly, "Part__Feature094", 1017, 1966.787),
        "Part__Feature094 Face1017",
    )
    plate = extrusion(document, group, "CameraPlate", "Editable angled camera plate", plate_profile, 5.0, True, "CameraPlateThickness")
    document.recompute()
    interface_clearance = document.addObject("Part::Feature", "InterfaceClearance")
    interface_clearance.Label = "Exact external wrist-clearance interface"
    interface_clearance.addProperty("App::PropertyString", "DerivedFrom", "Source")
    interface_clearance.addProperty("App::PropertyString", "Purpose", "Source")
    interface_clearance.DerivedFrom = "Part__Feature094 minus native Wrist BodyExtrusion"
    interface_clearance.Purpose = "Preserves the Fusion XRef clearance not expressible as a native prism"
    interface_clearance.Shape = body.Shape.cut(reference)
    interface_clearance.Visibility = False
    group.addObject(interface_clearance)
    bosses = [
        cylinder_from_source_face(
            document,
            group,
            f"Boss{number}",
            "Editable wrist-camera mounting boss",
            source_cylinder_face(assembly, "Part__Feature094", index, 47.124),
            (("Radius", "BossRadius"), ("Height", "BossDepth")),
        )
        for number, index in enumerate((1, 3, 5, 7), 1)
    ]
    boss_holes = [
        cylinder_from_source_face(
            document,
            group,
            f"BossHole{number}",
            "Camera or gripper screw hole",
            source_cylinder_face(assembly, "Part__Feature094", index, 75.398),
            (("Radius", "BossHoleRadius"), ("Height", "BossHoleLength")),
        )
        for number, index in enumerate((1018, 1019, 1020, 1021), 1)
    ]
    final = cut(
        document,
        group,
        "Final",
        title,
        fuse(document, group, "MountBody", "Wrist camera-mount body", [body, plate, *bosses]),
        fuse(document, group, "ClearanceTools", "Wrist-camera clearance tools", [interface_clearance, *boss_holes]),
    )
    finish(document, group, final, PARTS / "wrist_camera_mount.FCStd", title, reference)


def build_omni_wheel_mount(assembly):
    title = "omni-wheel mount"
    target = Mesh.Mesh("URDF/meshes/omni_wheel_mount-v5-2.stl")
    target_box = bounds(target)
    front_top = target_box[2] + 4.0
    web_start = front_top + 0.3
    web_end = web_start + 2.575
    hub_start = web_end + 0.3
    hub_end = target_box[5] - 0.475
    front_profile_shape = mesh_slice_profile(target, target_box[2] + 2.0, target_box[2])
    web_profile_shape = mesh_slice_profile(target, 0.0, web_start)
    hub_profile_shape = mesh_slice_profile(target, 5.0, hub_start)
    document, group = new_model(
        "LeKiwiOmniWheelMount",
        title,
        FrontThickness=4.0,
        WebThickness=2.575,
        HubDepth=6.35,
    )

    def transition_layers(name, label, lower, upper):
        height = (upper - lower) / 3
        items = []
        for number in range(3):
            start = lower + number * height
            level = start + height / 2
            shape = mesh_slice_profile(target, level, start)
            section = profile(
                document,
                group,
                f"{name}Profile{number + 1}",
                f"Canonical STL {label} section {number + 1}",
                shape,
                f"omni_wheel_mount-v5-2.stl slice z={level:.4f}",
            )
            items.append(extrusion(document, group, f"{name}{number + 1}", f"Editable {label} section {number + 1}", section, height))
        return items

    front_profile = profile(document, group, "FrontProfile", "Canonical STL front profile", front_profile_shape, "omni_wheel_mount-v5-2.stl slice z=-3.5875")
    front = extrusion(document, group, "FrontPlate", "Editable front mounting plate", front_profile, 4.0, False, "FrontThickness")
    web_profile = profile(document, group, "WebProfile", "Canonical STL web profile", web_profile_shape, "omni_wheel_mount-v5-2.stl slice z=0")
    web = extrusion(document, group, "StructuralWeb", "Editable structural web", web_profile, 2.575, False, "WebThickness")
    hub_profile = profile(document, group, "HubProfile", "Canonical STL hub profile", hub_profile_shape, "omni_wheel_mount-v5-2.stl slice z=5")
    hub = extrusion(document, group, "Hub", "Editable servo hub", hub_profile, 6.35, False, "HubDepth")
    final = fuse(
        document,
        group,
        "Final",
        title,
        [
            front,
            *transition_layers("LowerTransition", "lower web transition", front_top, web_start),
            web,
            *transition_layers("UpperTransition", "upper hub transition", web_end, hub_start),
            hub,
            *transition_layers("TopCap", "hub top cap", hub_end, target_box[5]),
        ],
    )
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
