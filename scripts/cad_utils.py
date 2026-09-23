import json
import math
import re
from pathlib import Path


# Links whose Pi-case reference geometry is retained in the baseline URDF for
# historical/dimensional purposes but is never exported as installed hardware.
PI_CASE_LINKS = frozenset({"Bottom-V2-v3", "Top-V2-v2"})

# The SO-101 visual override deliberately paints every follower part yellow.
SO101_YELLOW_RGBA = "1.0 0.82 0.12 1.0"

NATIVE_PARTS_FILE = Path("cad/native_parts.json")


def require(condition, message):
    """Raise SystemExit with MESSAGE unless CONDITION is truthy.

    Verify scripts use this instead of a bare ``assert`` so a failed check
    reports a clear message even when Python is run with ``-O``.
    """
    if not condition:
        raise SystemExit(message)


def object_name(prefix, name):
    return prefix + re.sub(r"[^0-9A-Za-z_]", "_", name)


def mesh_filename(name):
    return re.sub(r"[^0-9A-Za-z_.-]", "_", name) + ".stl"


def native_part_replacements(path=NATIVE_PARTS_FILE):
    """Map URDF link name to its native-part reference mesh, where defined.

    Reads ``cad/native_parts.json``; entries without a ``reference_mesh`` are
    left out, matching every prior inline copy of this comprehension.
    """
    return {
        link: item["reference_mesh"]
        for item in json.loads(Path(path).read_text())
        if item.get("reference_mesh")
        for link in item["links"]
    }


def bounds(shape_or_mesh):
    box = shape_or_mesh.BoundBox
    return box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax


def bounds_error(left, right):
    scale = max(right[3] - right[0], right[4] - right[1], right[5] - right[2], 1.0)
    return sum(abs(a - b) for a, b in zip(left, right)) / scale


def urdf_matrix(origin):
    import FreeCAD as App

    x, y, z = (float(item) * 1000.0 for item in origin.get("xyz", "0 0 0").split())
    roll, pitch, yaw = (float(item) for item in origin.get("rpy", "0 0 0").split())
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
