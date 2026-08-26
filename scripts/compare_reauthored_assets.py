"""Compare native FreeCAD exports with the original URDF meshes.

The comparison is deliberately separate from the inexpensive bounding-box and
volume migration check. It samples each mesh surface in both directions and
finds the closest point on the opposite triangulated surface.
"""

import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import FreeCAD as App
import Mesh


URDF = Path("URDF/LeKiwi.urdf")
MAPPING = Path("cad/reference_mapping.json")
OUTPUT = Path("cad/validation/reauthored_asset_comparison.json")
# ponytail: sampled rather than full Hausdorff; raise this or use a full-mesh
# analysis when sub-sample local deviations matter.
SAMPLES_PER_DIRECTION = 256
MAX_SURFACE_ERROR_MM = 0.25
MAX_P95_ERROR_MM = 0.10
LEAF_SIZE = 16


def numbers(value, scale=1.0):
    return [float(item) * scale for item in value.split()]


def matrix(origin):
    x, y, z = numbers(origin.get("xyz", "0 0 0"), 1000.0)
    roll, pitch, yaw = numbers(origin.get("rpy", "0 0 0"))
    cosine, sine = math.cos, math.sin
    values = (
        (cosine(yaw) * cosine(pitch), cosine(yaw) * sine(pitch) * sine(roll) - sine(yaw) * cosine(roll), cosine(yaw) * sine(pitch) * cosine(roll) + sine(yaw) * sine(roll), x),
        (sine(yaw) * cosine(pitch), sine(yaw) * sine(pitch) * sine(roll) + cosine(yaw) * cosine(roll), sine(yaw) * sine(pitch) * cosine(roll) - cosine(yaw) * sine(roll), y),
        (-sine(pitch), cosine(pitch) * sine(roll), cosine(pitch) * cosine(roll), z),
        (0.0, 0.0, 0.0, 1.0),
    )
    result = App.Matrix()
    for row in range(4):
        for column in range(4):
            setattr(result, f"A{row + 1}{column + 1}", values[row][column])
    return result


def sampled_points(mesh, count):
    facets = mesh.Facets
    if not facets:
        raise RuntimeError("mesh has no facets")
    sample_count = min(count, len(facets))
    indices = [round(index * (len(facets) - 1) / max(sample_count - 1, 1)) for index in range(sample_count)]
    points = []
    for index in indices:
        vertices = [tuple(vertex) for vertex in facets[index].Points]
        points.append(tuple(sum(vertex[axis] for vertex in vertices) / len(vertices) for axis in range(3)))
        points.append(vertices[index % len(vertices)])
    return points


def quantile(values, fraction):
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def dot(left, right):
    return sum(a * b for a, b in zip(left, right))


def subtract(left, right):
    return tuple(a - b for a, b in zip(left, right))


def point_segment_distance_squared(point, first, second):
    segment = subtract(second, first)
    length_squared = dot(segment, segment)
    if length_squared == 0:
        return dot(subtract(point, first), subtract(point, first))
    ratio = max(0.0, min(1.0, dot(subtract(point, first), segment) / length_squared))
    closest = tuple(first[axis] + ratio * segment[axis] for axis in range(3))
    difference = subtract(point, closest)
    return dot(difference, difference)


def point_triangle_distance_squared(point, triangle):
    """Squared closest distance using the region tests from Real-Time Collision Detection."""
    first, second, third = triangle
    first_to_point = subtract(point, first)
    first_to_second = subtract(second, first)
    first_to_third = subtract(third, first)
    normal = (
        first_to_second[1] * first_to_third[2] - first_to_second[2] * first_to_third[1],
        first_to_second[2] * first_to_third[0] - first_to_second[0] * first_to_third[2],
        first_to_second[0] * first_to_third[1] - first_to_second[1] * first_to_third[0],
    )
    if dot(normal, normal) < 1e-18:
        return min(
            point_segment_distance_squared(point, first, second),
            point_segment_distance_squared(point, second, third),
            point_segment_distance_squared(point, third, first),
        )
    dot_first_second = dot(first_to_second, first_to_point)
    dot_first_third = dot(first_to_third, first_to_point)
    if dot_first_second <= 0 and dot_first_third <= 0:
        return dot(first_to_point, first_to_point)

    second_to_point = subtract(point, second)
    dot_second_second = dot(first_to_second, second_to_point)
    dot_second_third = dot(first_to_third, second_to_point)
    if dot_second_second >= 0 and dot_second_third <= dot_second_second:
        return dot(second_to_point, second_to_point)

    edge_first_second = dot_first_second * dot_second_third - dot_second_second * dot_first_third
    if edge_first_second <= 0 and dot_first_second >= 0 and dot_second_second <= 0:
        ratio = dot_first_second / (dot_first_second - dot_second_second)
        offset = tuple(ratio * value for value in first_to_second)
        return dot(subtract(first_to_point, offset), subtract(first_to_point, offset))

    third_to_point = subtract(point, third)
    dot_third_second = dot(first_to_second, third_to_point)
    dot_third_third = dot(first_to_third, third_to_point)
    if dot_third_third >= 0 and dot_third_second <= dot_third_third:
        return dot(third_to_point, third_to_point)

    edge_first_third = dot_third_second * dot_first_third - dot_first_second * dot_third_third
    if edge_first_third <= 0 and dot_first_third >= 0 and dot_third_third <= 0:
        ratio = dot_first_third / (dot_first_third - dot_third_third)
        offset = tuple(ratio * value for value in first_to_third)
        return dot(subtract(first_to_point, offset), subtract(first_to_point, offset))

    edge_second_third = dot_second_second * dot_third_third - dot_third_second * dot_second_third
    if edge_second_third <= 0 and dot_second_third - dot_second_second >= 0 and dot_third_second - dot_third_third >= 0:
        ratio = (dot_second_third - dot_second_second) / ((dot_second_third - dot_second_second) + (dot_third_second - dot_third_third))
        edge = subtract(third, second)
        offset = tuple(ratio * value for value in edge)
        return dot(subtract(second_to_point, offset), subtract(second_to_point, offset))

    denominator = 1.0 / (edge_first_second + edge_first_third + edge_second_third)
    second_ratio = edge_first_third * denominator
    third_ratio = edge_first_second * denominator
    closest = tuple(
        first[axis] + second_ratio * first_to_second[axis] + third_ratio * first_to_third[axis]
        for axis in range(3)
    )
    difference = subtract(point, closest)
    return dot(difference, difference)


def triangle_entry(facet):
    triangle = tuple(tuple(vertex) for vertex in facet.Points)
    lower = tuple(min(vertex[axis] for vertex in triangle) for axis in range(3))
    upper = tuple(max(vertex[axis] for vertex in triangle) for axis in range(3))
    center = tuple((lower[axis] + upper[axis]) / 2 for axis in range(3))
    return triangle, lower + upper, center


def combined_bounds(entries):
    return tuple(
        min(entry[1][axis] for entry in entries) if axis < 3 else max(entry[1][axis] for entry in entries)
        for axis in range(6)
    )


def make_tree(entries):
    bounds = combined_bounds(entries)
    if len(entries) <= LEAF_SIZE:
        return bounds, entries, ()
    axis = max(range(3), key=lambda index: bounds[index + 3] - bounds[index])
    entries.sort(key=lambda entry: entry[2][axis])
    midpoint = len(entries) // 2
    return bounds, (), (make_tree(entries[:midpoint]), make_tree(entries[midpoint:]))


def bounds_distance_squared(point, bounds):
    return sum(
        (bounds[axis] - point[axis]) ** 2 if point[axis] < bounds[axis]
        else (point[axis] - bounds[axis + 3]) ** 2 if point[axis] > bounds[axis + 3]
        else 0.0
        for axis in range(3)
    )


def nearest_distance_squared(point, tree, best=float("inf")):
    bounds, entries, children = tree
    if bounds_distance_squared(point, bounds) >= best:
        return best
    if entries:
        return min(best, *(point_triangle_distance_squared(point, entry[0]) for entry in entries))
    ordered = sorted(children, key=lambda child: bounds_distance_squared(point, child[0]))
    for child in ordered:
        best = nearest_distance_squared(point, child, best)
    return best


def surface_distances(source, target):
    tree = make_tree([triangle_entry(facet) for facet in target.Facets])
    return [math.sqrt(nearest_distance_squared(point, tree)) for point in sampled_points(source, SAMPLES_PER_DIRECTION)]


def filename(name):
    return re.sub(r"[^0-9A-Za-z_.-]", "_", name) + ".stl"


if set(sys.argv[1:]) - {"--strict"}:
    raise SystemExit("usage: compare_reauthored_assets.py [--strict]")

strict = "--strict" in sys.argv
root = ET.parse(URDF).getroot()
visuals = {link.get("name"): link.find("visual") for link in root.findall("link")}
entries = []
for item in json.loads(MAPPING.read_text()):
    if not item["source_kind"].startswith("native FreeCAD"):
        continue
    name = item["urdf_link"]
    visual = visuals.get(name)
    mesh_xml = visual.find("geometry/mesh") if visual is not None else None
    if mesh_xml is None:
        raise RuntimeError(f"{name}: missing original URDF visual mesh")
    original = Mesh.Mesh(str(URDF.parent / mesh_xml.get("filename")))
    origin = visual.find("origin")
    original.transform(matrix(origin if origin is not None else ET.Element("origin")))
    generated_path = URDF.parent / "meshes/reauthored" / filename(name)
    if not generated_path.is_file():
        raise RuntimeError(f"{name}: missing generated mesh {generated_path}")
    generated = Mesh.Mesh(str(generated_path))
    distances = surface_distances(original, generated) + surface_distances(generated, original)
    maximum = max(distances)
    p95 = quantile(distances, 0.95)
    rms = math.sqrt(sum(value * value for value in distances) / len(distances))
    entry = {
        "urdf_link": name,
        "original_mesh": mesh_xml.get("filename"),
        "generated_mesh": str(generated_path.relative_to(URDF.parent)),
        "method": "bidirectional sampled closest point-to-triangle surface distance",
        "samples": len(distances),
        "max_surface_error_mm": maximum,
        "p95_surface_error_mm": p95,
        "rms_surface_error_mm": rms,
        "status": "pass" if maximum <= MAX_SURFACE_ERROR_MM and p95 <= MAX_P95_ERROR_MM else "fail",
    }
    entries.append(entry)
    print(
        f"{name}: {entry['status']} max={maximum:.3f} mm p95={p95:.3f} mm rms={rms:.3f} mm "
        f"({len(distances)} samples)"
    )

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps(
        {
            "method": "bidirectional sampled closest point-to-triangle surface distance",
            "samples_per_direction": SAMPLES_PER_DIRECTION * 2,
            "max_surface_error_mm": MAX_SURFACE_ERROR_MM,
            "max_p95_error_mm": MAX_P95_ERROR_MM,
            "entries": entries,
        },
        indent=2,
    )
    + "\n"
)
failures = [entry["urdf_link"] for entry in entries if entry["status"] == "fail"]
print(f"wrote {OUTPUT}; {len(entries) - len(failures)}/{len(entries)} native link instances pass")
if strict and failures:
    raise SystemExit("surface-fidelity failures: " + ", ".join(failures))
