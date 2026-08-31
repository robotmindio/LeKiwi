import math
import re

import FreeCAD as App


def mesh_filename(name):
    return re.sub(r"[^0-9A-Za-z_.-]", "_", name) + ".stl"


def bounds(shape_or_mesh):
    box = shape_or_mesh.BoundBox
    return box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax


def bounds_error(left, right):
    scale = max(right[3] - right[0], right[4] - right[1], right[5] - right[2], 1.0)
    return sum(abs(a - b) for a, b in zip(left, right)) / scale


def urdf_matrix(origin):
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
