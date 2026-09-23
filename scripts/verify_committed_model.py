"""Fail when a fresh export differs from the committed ROS model.

FreeCAD and OpenSCAD reorder triangles and rotate each triangle's vertex cycle
between runs, so meshes are compared as canonical triangle sets. Text outputs
(Xacro and expanded URDF) must match byte for byte.
"""

import sys
from pathlib import Path

import numpy as np

TEXT_OUTPUTS = ("URDF/LeKiwi.urdf.xacro", "URDF/LeKiwi.urdf")
MESH_DIRS = ("URDF/meshes/reauthored", "URDF/meshes/so101")


def triangles(path):
    data = path.read_bytes()
    count = int.from_bytes(data[80:84], "little")
    if len(data) != 84 + count * 50:
        raise SystemExit(f"{path}: not a binary STL")
    return np.frombuffer(
        data, offset=84, count=count,
        dtype=np.dtype([("normal", "<f4", (3,)), ("v", "<f4", (3, 3)), ("attr", "<u2")]),
    )["v"].astype(np.float64)


def canonical(tris):
    # Rotate each cycle to start at its lexicographically smallest vertex
    # (keeps winding), then sort the triangles.
    first = np.lexsort(tris.transpose(2, 0, 1)[::-1], axis=-1)[:, 0]
    order = (first[:, None] + np.arange(3)) % 3
    rotated = np.take_along_axis(tris, order[:, :, None], axis=1).reshape(len(tris), 9)
    return rotated[np.lexsort(rotated.T[::-1])]


def same_mesh(built, committed):
    a, b = triangles(built), triangles(committed)
    if a.shape != b.shape:
        return False
    tolerance = 1e-6 * max(np.ptp(b.reshape(-1, 3), axis=0).max(), 1e-9)
    return np.allclose(canonical(a), canonical(b), rtol=0, atol=tolerance)


def main(build, committed):
    errors = []
    for name in TEXT_OUTPUTS:
        if (build / name).read_bytes() != (committed / name).read_bytes():
            errors.append(f"{name} differs from a fresh export")
    for directory in MESH_DIRS:
        built = {p.name for p in (build / directory).glob("*.stl")}
        kept = {p.name for p in (committed / directory).glob("*.stl")}
        errors += [f"{directory}/{n} is not produced by the export" for n in sorted(kept - built)]
        errors += [f"{directory}/{n} is produced but not committed" for n in sorted(built - kept)]
        for name in sorted(built & kept):
            if not same_mesh(build / directory / name, committed / directory / name):
                errors.append(f"{directory}/{name} geometry differs from a fresh export")
    if errors:
        raise SystemExit("committed model is stale; run scripts/export_robot.sh:\n  " + "\n  ".join(errors))
    print("committed Xacro, URDF and meshes match a fresh export")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify_committed_model.py BUILD_ROOT COMMITTED_ROOT")
    main(Path(sys.argv[1]), Path(sys.argv[2]))
