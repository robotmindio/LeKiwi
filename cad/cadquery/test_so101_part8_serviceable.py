"""Build/export the pilot and check interfaces, caps and sampled URDF clearance."""

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
    COVER_HEAD_Y,
    COVER_SCREWS,
    INTERFACE_REGIONS,
    ServiceParameters,
    _source,
    parts,
)
from so101_scene import URDF, placements, reference, wrist_scene
from so101_wrist import PARTS

OUTPUT = Path(__file__).resolve().parents[1] / "generated/part8-serviceable"
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


def check_tool_access(meshes):
    """Sample a 6 mm straight shaft with 60 mm reach outside the side screws."""
    clearances = {}
    for name, side in (("cover_left", -1), ("cover_right", 1)):
        points = np.array(
            [
                (x + radius * np.cos(angle), side * y, z + radius * np.sin(angle))
                for x, z in COVER_SCREWS
                for y in np.linspace(COVER_HEAD_Y + 0.1, COVER_HEAD_Y + 60, 61)
                for radius in (0, 3)
                for angle in np.linspace(0, 2 * np.pi, 37)
            ]
        )
        nearest = float("inf")
        obstacles = [
            (name, mesh)
            for _, name, mesh in wrist_scene(
                {},
                {"wrist_link", "lower_arm_link", "gripper_link"},
            )
        ] + list(meshes.items())
        for obstacle_name, mesh in obstacles:
            obstacle = field(mesh)
            distance = min(obstacle.EvaluateFunction(point) for point in points)
            assert distance >= 0, (name, obstacle_name, distance)
            nearest = min(nearest, distance)
        clearances[name] = nearest
    return {
        "pose": "All URDF joints at zero; straight side access, no service rotation.",
        "shaft_diameter_mm": 6,
        "reach_mm": 60,
        "sampled_min_clearance_mm": clearances,
        "scope": "Shaft only; handle, fastener extraction and physical tool access still need bench checking.",
    }


def main():
    for invalid in (float("nan"), -1, 20):
        try:
            ServiceParameters(cover_wall=invalid).validate()
        except ValueError:
            pass
        else:
            raise AssertionError("invalid dimensions accepted")
    solids = {name: part.val() for name, part in parts().items()}
    assert (
        abs(solids["cradle"].BoundingBox().ymax - FRAME_OUTER_Y) < 1e-6
    ), "no projecting mount arms"
    for name, side in (("cover_left", -1), ("cover_right", 1)):
        for x in (0, 5, 10):
            assert solids[name].isInside(
                (x, side * (FRAME_OUTER_Y - 1), -21), 1e-6
            ), "no ventilation slots"
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
    for name in ("cover_left", "cover_right"):
        assert (
            max(
                abs(v)
                for v in (
                    solids[name].BoundingBox().ymin,
                    solids[name].BoundingBox().ymax,
                )
            )
            <= FRAME_OUTER_Y + 1e-6
        ), "cover projects beyond the frame"
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
    for name, side in (("cover_left", -1), ("cover_right", 1)):
        for travel in (0, 0.25, 0.5, 1, 2, 4, 8, 16, 30, 45):
            overlap = (
                solids[name]
                .translate((0, side * travel, 0))
                .intersect(solids["cradle"])
            )
            assert overlap.isValid() and abs(overlap.Volume()) < 1e-6, (name, travel)
    overlap = solids["cover_left"].intersect(solids["cover_right"])
    assert overlap.isValid() and abs(overlap.Volume()) < 1e-6
    exported = {}
    for name, solid in {"original": original, **solids}.items():
        exported[name] = export_stl(solid, OUTPUT / f"{name}.stl")
        print(f"Exported {name}: checked closed single mesh", flush=True)
    for name, side in (("cover_left", -1), ("cover_right", 1)):
        oriented = solids[name].rotate((0, 0, 0), (1, 0, 0), 90 * side)
        oriented = oriented.translate((0, 0, -oriented.BoundingBox().zmin))
        export_stl(oriented, OUTPUT / f"{name}_print.stl")
    oriented = solids["cradle"].rotate((0, 0, 0), (0, 1, 0), -90)
    oriented = oriented.translate((0, 0, -oriented.BoundingBox().zmin))
    export_stl(oriented, OUTPUT / "cradle_print.stl")
    assembly = cq.Assembly()
    for name, solid in solids.items():
        assembly.add(solid, name=name)
    assembly.save(str(OUTPUT / "serviceable.step"))
    meshes = {name: read_mesh(OUTPUT / f"{name}.stl") for name in exported}
    clearance = check_clearance(meshes)
    tool_access = check_tool_access(meshes)
    report = {
        "units": "mm",
        "parameters": vars(ServiceParameters()),
        "source_sha256": hashlib.sha256(PARTS["flex_body"].read_bytes()).hexdigest(),
        "urdf_sha256": hashlib.sha256(URDF.read_bytes()).hexdigest(),
        "exact_interfaces": list(INTERFACE_REGIONS),
        "joint_datums": datums,
        "cover_removal": "No CAD overlap at 10 translations along each cover's outward Y direction, screws removed.",
        "clearance": clearance,
        "tool_access": tool_access,
        "meshes": exported,
        "qualification": "Geometric prototype: loads, fatigue, thermal performance, print strength and physical assembly have not been tested.",
    }
    (OUTPUT / "checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
