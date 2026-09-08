"""Export the single-piece cradle and check interfaces and sampled motion."""

import hashlib
import json
from math import ceil, degrees, sqrt
from pathlib import Path

import cadquery as cq
import numpy as np
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkFiltersCore import vtkImplicitPolyDataDistance
from vtkmodules.vtkIOGeometry import vtkSTLReader

from cad_checks import export_stl
from so101_part8_serviceable import (
    FRAME_OUTER_Y,
    SEAT_BOTTOM_Z,
    INTERFACE_REGIONS,
    _source,
    cradle,
)
from so101_scene import URDF, placements, reference, wrist_scene, transform_mesh
from so101_wrist import PARTS

OUTPUT = Path(__file__).resolve().parents[1] / "generated/part8-smooth"
TOLERANCE = 0.08  # mm; exported surface deflection is 0.02 mm.


def read_mesh(path):
    reader = vtkSTLReader()
    reader.SetFileName(str(path))
    reader.Update()
    return reader.GetOutput()


def field(mesh):
    distance = vtkImplicitPolyDataDistance()
    distance.SetInput(mesh)
    return distance


def samples(mesh):
    points = vtk_to_numpy(mesh.GetPoints().GetData())
    triangles = vtk_to_numpy(mesh.GetPolys().GetConnectivityArray()).reshape(-1, 3)
    vertices = points[triangles]
    return np.concatenate(
        (
            points,
            vertices.mean(axis=1),
            (vertices[:, 0] + vertices[:, 1]) / 2,
            (vertices[:, 1] + vertices[:, 2]) / 2,
            (vertices[:, 2] + vertices[:, 0]) / 2,
        )
    )


def in_bounds(points, mesh):
    bounds = mesh.GetBounds()
    return points[np.all((points >= bounds[::2]) & (points <= bounds[1::2]), axis=1)]


def check_clearance(meshes):
    """Compare new material against the real meshes, never equal total volume.

    ponytail: finite surface/angle sampling is not a continuous collision proof;
    use swept-solid collision checking before claiming certified clearance.
    """
    original = field(meshes["original"])
    candidates = {}
    for name, mesh in meshes.items():
        if name == "original":
            continue
        points = samples(mesh)
        added = points[[original.EvaluateFunction(p) > TOLERANCE for p in points]]
        candidates[name] = (mesh, field(mesh), added)
    robot, _ = reference()
    cases = [({}, {"wrist_link"})]
    ranges = {}
    for joint_name, link in (
        ("wrist_roll", "gripper_link"),
        ("wrist_flex", "lower_arm_link"),
    ):
        limit = robot.find(f"joint[@name='{joint_name}']/limit")
        low, high = (float(limit.attrib[key]) for key in ("lower", "upper"))
        angles = np.linspace(low, high, ceil(degrees(high - low) / 2) + 1)
        ranges[joint_name] = {
            "degrees": [degrees(low), degrees(high)],
            "poses": len(angles),
        }
        cases.extend(({joint_name: float(angle)}, {link}) for angle in angles)
    for index, (angles, links) in enumerate(cases):
        for link, obstacle_name, obstacle in wrist_scene(angles, links):
            obstacle_field = field(obstacle)
            obstacle_points = samples(obstacle)
            for name, (mesh, candidate_field, added) in candidates.items():
                forward = in_bounds(added, obstacle)
                hits = [
                    p.tolist()
                    for p in forward
                    if obstacle_field.EvaluateFunction(p) < -TOLERANCE
                ]
                reverse = in_bounds(obstacle_points, mesh)
                hits += [
                    p.tolist()
                    for p in reverse
                    if candidate_field.EvaluateFunction(p) < -TOLERANCE
                    and original.EvaluateFunction(p) > TOLERANCE
                ]
                assert not hits, (name, obstacle_name, angles, len(hits), hits[:3])
        if index % 25 == 0:
            print(f"Clearance pose {index + 1}/{len(cases)} passed", flush=True)
    return {
        "ranges": ranges,
        "penetration_tolerance_mm": TOLERANCE,
        "scope": "Internal servo and immediate neighboring URDF visuals; vertices, edge midpoints and triangle centroids. No newly detected interference relative to upstream part.",
        "limitations": "Finite sampling, not continuous swept-volume proof. Non-neighbor whole-arm collisions and physical fit are not certified.",
    }


def check_motor_access(meshes):
    """The new shell must not add obstructions to the original front entry.

    ponytail: this compares sampled straight translations to upstream; existing
    guide/clip interference means it does not prove a rigid, force-free assembly.
    """
    original, candidate = (field(meshes[name]) for name in ("original", "cradle"))
    added = samples(meshes["cradle"])
    added = added[[original.EvaluateFunction(p) > TOLERANCE for p in added]]
    for _, name, motor in wrist_scene({}, {"wrist_link"}):
        for travel in np.linspace(0, 60, 61):
            moved = transform_mesh(motor, cq.Location((float(travel), 0, 0)))
            motor_field = field(moved)
            hits = [
                p
                for p in in_bounds(samples(moved), meshes["cradle"])
                if candidate.EvaluateFunction(p) < -TOLERANCE
                and original.EvaluateFunction(p) > TOLERANCE
            ]
            hits += [
                p
                for p in in_bounds(added, moved)
                if motor_field.EvaluateFunction(p) < -TOLERANCE
            ]
            assert not hits, (name, travel, len(hits), hits[:3])
    return "No newly detected front-entry obstruction at 61 translations over 60 mm. Existing upstream clip/guide interference and physical assembly still need bench verification."


def main():
    solids = {"cradle": cradle().val()}
    assert abs(solids["cradle"].BoundingBox().ymax - FRAME_OUTER_Y) < 1e-6
    assert (
        solids["cradle"].BoundingBox().zmin >= SEAT_BOTTOM_Z - 1e-5
    ), "bottom tooth remains"
    for side in (-1, 1):
        for x in (0, 5, 10):
            for z in (-8, -15.5, -21):
                assert solids["cradle"].isInside(
                    (x, side * (FRAME_OUTER_Y - 1), z), 1e-6
                ), "side wall is not continuous"
    robot, visuals = reference()
    frames = placements({})
    part_pose = next(
        pose for _, name, pose, _ in visuals if name == "wrist_roll_pitch_so101_v2"
    )
    anchor = (frames["wrist_link"] * part_pose).inverse
    datums = {}
    for joint, expected_point, expected_axis in (
        ("wrist_flex", (-18.1, 0, 28), (1, 0, 0)),
        ("wrist_roll", (0, 0, -33.1), (0, 0, 1)),
    ):
        child = robot.find(f"joint[@name='{joint}']/child").attrib["link"]
        transform = (anchor * frames[child]).wrapped.Transformation()
        point = tuple(transform.Value(i, 4) for i in (1, 2, 3))
        axis = tuple(transform.Value(i, 3) for i in (1, 2, 3))
        assert np.allclose(point, expected_point, atol=0.001)
        assert np.allclose(axis, expected_axis, atol=0.00001)
        datums[joint] = {"point_mm": point, "axis": axis}
    original = _source()
    # The outer ear silhouette is deliberately different; the counterbore
    # seating planes and diameters must still match the pinned source exactly.
    for x in (-21.2, 21.1):
        region = cq.Solid.makeBox(0.1, 16, 16, (x, -8, 20))
        expected = original.intersect(region)
        actual = solids["cradle"].intersect(region)
        assert abs(expected.cut(actual).Volume()) < 1e-5
        assert abs(actual.cut(expected).Volume()) < 1e-5
    for x in (-27.1, 21.1):
        for y in (-7 / sqrt(2), 7 / sqrt(2)):
            for z in (28 - 7 / sqrt(2), 28 + 7 / sqrt(2)):
                bore = cq.Solid.makeCylinder(2.7, 6, (x, y, z), (1, 0, 0))
                assert abs(solids["cradle"].intersect(bore).Volume()) < 1e-5
    # No old sloping deck fragments, no upper-ear patch boundary on the rim.
    assert not any(
        3.4001 < face.Center().z < 18 and -13.3 < face.Center().x < 17
        for face in solids["cradle"].Faces()
    ), "unexpected raised deck geometry"
    for edge in solids["cradle"].Edges():
        bounds = edge.BoundingBox()
        assert not (
            abs(bounds.zmin - 20) < 1e-5
            and abs(bounds.zmax - 20) < 1e-5
            and (bounds.xmin < -22.1 or bounds.xmax > 22.1)
        ), "external seam at old ear patch boundary"
    for name, (size, corner) in INTERFACE_REGIONS.items():
        region = cq.Solid.makeBox(*size, corner)
        retained = original.intersect(region)
        actual = solids["cradle"].intersect(region)
        removed, added = retained.cut(actual), actual.cut(retained)
        assert removed.isValid() and added.isValid(), name
        assert abs(removed.Volume()) < 1e-5 and abs(added.Volume()) < 1e-5, (
            name,
            removed.Volume(),
            added.Volume(),
        )
    exported = {}
    for name, solid in {"original": original, **solids}.items():
        exported[name] = export_stl(solid, OUTPUT / f"{name}.stl")
        print(f"Exported {name}: checked closed single mesh", flush=True)
    oriented = solids["cradle"].rotate((0, 0, 0), (0, 1, 0), -90)
    oriented = oriented.translate((0, 0, -oriented.BoundingBox().zmin))
    export_stl(oriented, OUTPUT / "cradle_print.stl")
    cq.exporters.export(solids["cradle"], str(OUTPUT / "cradle.step"))
    meshes = {name: read_mesh(OUTPUT / f"{name}.stl") for name in exported}
    clearance = check_clearance(meshes)
    motor_access = check_motor_access(meshes)
    report = {
        "units": "mm",
        "source_sha256": hashlib.sha256(PARTS["flex_body"].read_bytes()).hexdigest(),
        "urdf_sha256": hashlib.sha256(URDF.read_bytes()).hexdigest(),
        "exact_interfaces": list(INTERFACE_REGIONS),
        "joint_datums": datums,
        "travel_stop": "Bottom tooth removed by user request. Software limits unchanged; the original physical stop is no longer present.",
        "clearance": clearance,
        "motor_access": motor_access,
        "meshes": exported,
        "qualification": "Geometric prototype: loads, fatigue, thermal performance, print strength and physical assembly have not been tested.",
    }
    (OUTPUT / "checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
