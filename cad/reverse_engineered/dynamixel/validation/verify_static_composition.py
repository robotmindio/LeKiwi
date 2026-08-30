"""Sample-validate both public static-side bodies and the legacy-hole patch.

Run under FreeCAD with uncommitted STL exports of the public Fusion source's
small and large bodies, in that order.  The large body is compared directly and
bidirectionally with its corresponding target component.  The small body's
unpatched source export is compared everywhere except the one fitted legacy
through-hole, whose finite cylinder is checked separately.

The proof intentionally reports ``compositional_pass`` rather than a direct
patched-small-body export pass.
"""

import argparse
import json
import math
import runpy
from pathlib import Path

import Mesh


ROOT = Path(__file__).resolve().parents[4]
COMPARE = runpy.run_path(str(ROOT / "scripts/compare_reauthored_assets.py"))
TARGET_DEFAULT = ROOT / "3DPrintMeshes/dynamixel_specific/modified_static_side_with_mount.stl"
SMALL_TARGET_FACETS = 2320
LARGE_TARGET_FACETS = 7832
MAX_ERROR = COMPARE["MAX_SURFACE_ERROR_MM"]
P95_ERROR = COMPARE["MAX_P95_ERROR_MM"]

# Values fitted from the target's 52 cylindrical side faces, in mm.
RADIUS = 3.149941806669
START = (-19.125301303971, -24.300928850665, -70.134244680553)
END = (-19.125301303971, -22.397081810826, -73.649901720044)
DELTA = tuple(end - start for start, end in zip(START, END))
LENGTH = math.sqrt(sum(value * value for value in DELTA))
AXIS = tuple(value / LENGTH for value in DELTA)
FIT_TOLERANCE = 0.005


def subtract(left, right):
    return tuple(a - b for a, b in zip(left, right))


def dot(left, right):
    return sum(a * b for a, b in zip(left, right))


def norm(vector):
    return math.sqrt(dot(vector, vector))


def cross(left, right):
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def point_and_normal(facet):
    points = tuple(tuple(point) for point in facet.Points)
    center = tuple(sum(point[axis] for point in points) / 3 for axis in range(3))
    raw = cross(subtract(points[1], points[0]), subtract(points[2], points[0]))
    length = norm(raw)
    return points, center, tuple(value / length for value in raw)


def axial(point):
    offset = subtract(point, START)
    length = dot(offset, AXIS)
    radial = norm(subtract(offset, tuple(length * value for value in AXIS)))
    return length, radial


def hole_faces(mesh):
    faces = []
    for index, facet in enumerate(mesh.Facets):
        _, center, normal = point_and_normal(facet)
        length, radial = axial(center)
        if abs(dot(normal, AXIS)) < 0.25 and 2.6 < radial < 3.7 and -1 < length < LENGTH + 1:
            faces.append(index)
    if len(faces) != 52:
        raise RuntimeError(f"expected exactly 52 fitted hole faces, found {len(faces)}")
    return set(faces)


def fit_hole(mesh, faces):
    vertices = {point for index in faces for point in point_and_normal(mesh.Facets[index])[0]}
    lengths, radii = zip(*(axial(point) for point in vertices))
    mean_radius = sum(radii) / len(radii)
    radius_rms = math.sqrt(sum((radius - RADIUS) ** 2 for radius in radii) / len(radii))
    result = {
        "face_count": len(faces),
        "vertex_count": len(vertices),
        "radius_mm": mean_radius,
        "radius_rms_error_mm": radius_rms,
        "radius_max_error_mm": max(abs(radius - RADIUS) for radius in radii),
        "start_offset_mm": min(lengths),
        "end_offset_mm": max(lengths),
        "length_mm": max(lengths) - min(lengths),
    }
    if (result["radius_max_error_mm"] > FIT_TOLERANCE
            or abs(result["start_offset_mm"]) > FIT_TOLERANCE
            or abs(result["end_offset_mm"] - LENGTH) > FIT_TOLERANCE):
        raise RuntimeError("target hole does not fit the patch constants")
    return result


def metrics(values):
    if not values:
        raise RuntimeError("no surface samples")
    return {
        "samples": len(values),
        "max_surface_error_mm": max(values),
        "p95_surface_error_mm": COMPARE["quantile"](values, 0.95),
        "rms_surface_error_mm": math.sqrt(sum(value * value for value in values) / len(values)),
    }


def strict(result):
    return result["max_surface_error_mm"] <= MAX_ERROR and result["p95_surface_error_mm"] <= P95_ERROR


def directed(candidate, target):
    return metrics(COMPARE["surface_distances"](candidate, target))


def indexed_samples(mesh):
    facets = mesh.Facets
    count = min(COMPARE["SAMPLES_PER_DIRECTION"], len(facets))
    for index in [round(value * (len(facets) - 1) / max(count - 1, 1)) for value in range(count)]:
        points, center, _ = point_and_normal(facets[index])
        yield index, center
        yield index, points[index % len(points)]


def target_outside_hole(target, candidate, faces):
    tree = COMPARE["make_tree"]([COMPARE["triangle_entry"](facet) for facet in candidate.Facets])
    outside, failed_faces = [], set()
    for index, point in indexed_samples(target):
        distance = math.sqrt(COMPARE["nearest_distance_squared"](point, tree))
        if distance > MAX_ERROR:
            failed_faces.add(index)
        if index not in faces:
            outside.append(distance)
    if not failed_faces or not failed_faces <= faces:
        raise RuntimeError(f"target mismatches are not confined to fitted hole faces: {sorted(failed_faces - faces)}")
    return metrics(outside), sorted(failed_faces)


def target_components(path):
    components = Mesh.Mesh(str(path)).getSeparateComponents()
    counts = (SMALL_TARGET_FACETS, LARGE_TARGET_FACETS)
    selected = {
        count: [component for component in components if component.CountFacets == count]
        for count in counts
    }
    invalid = {count: len(matches) for count, matches in selected.items() if len(matches) != 1}
    if invalid:
        raise RuntimeError(f"expected one target component for each facet count {counts}, found {invalid}")
    return selected[SMALL_TARGET_FACETS][0], selected[LARGE_TARGET_FACETS][0]


def path(value):
    value = Path(value)
    return value if value.is_absolute() else ROOT / value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("small_candidate", help="unpatched exported public-source small-body STL (not committed)")
    parser.add_argument("large_candidate", help="exported public-source large-body STL (not committed)")
    parser.add_argument("--target", default=str(TARGET_DEFAULT), help="canonical two-body static-side STL")
    args = parser.parse_args()

    small_path, large_path, target_path = path(args.small_candidate), path(args.large_candidate), path(args.target)
    if not small_path.is_file() or not large_path.is_file() or not target_path.is_file():
        raise SystemExit("both source-body proxies and target must be existing STL files")
    small_candidate, large_candidate = Mesh.Mesh(str(small_path)), Mesh.Mesh(str(large_path))
    small_target, large_target = target_components(target_path)

    large_body_to_target = COMPARE["comparison"](large_candidate, large_target)
    if not strict(large_body_to_target):
        raise SystemExit("large source body failed direct bidirectional sampled surface validation")

    faces = hole_faces(small_target)
    small_candidate_to_target = directed(small_candidate, small_target)
    small_target_outside_hole_to_candidate, failed_faces = target_outside_hole(small_target, small_candidate, faces)
    if not strict(small_candidate_to_target) or not strict(small_target_outside_hole_to_candidate):
        raise SystemExit("surface-fidelity failure outside the fitted legacy hole")

    result = {
        "status": "compositional_pass",
        "method": "large-body direct bidirectional sampled surface pass plus small-body fitted finite-hole composition",
        "sampling": {
            "large_body": "bidirectional sampled closest point-to-triangle surface distance",
            "small_body": "sampled source-to-target and target-outside-hole closest point-to-triangle surface distance",
        },
        "small_candidate": str(small_path),
        "large_candidate": str(large_path),
        "target": str(target_path),
        "thresholds_mm": {"max_surface_error": MAX_ERROR, "p95_surface_error": P95_ERROR},
        "large_body_to_target": large_body_to_target,
        "small_candidate_to_target": small_candidate_to_target,
        "small_target_outside_hole_to_candidate": small_target_outside_hole_to_candidate,
        "target_hole": fit_hole(small_target, faces),
        "failing_target_face_indices": failed_faces,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
