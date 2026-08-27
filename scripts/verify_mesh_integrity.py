"""Reject unexpected non-manifold canonical URDF meshes."""

import json
from pathlib import Path

import Mesh


URDF = Path("URDF")
MAPPING = Path("cad/reference_mapping.json")
ACCEPTED_NON_MANIFOLD = {
    "meshes/4-Omni-Directional-Wheel_Single_Body-v1-2.stl",
    "meshes/4-Omni-Directional-Wheel_Single_Body-v1-1.stl",
    "meshes/4-Omni-Directional-Wheel_Single_Body-v1.stl",
}

paths = {
    item["mesh_filename"]
    for item in json.loads(MAPPING.read_text())
    if item["source_kind"] == "canonical URDF STL mesh reference"
}
non_manifold = {path for path in paths if Mesh.Mesh(str(URDF / path)).hasNonManifolds()}
if non_manifold != ACCEPTED_NON_MANIFOLD:
    raise RuntimeError(
        f"unexpected non-manifold meshes: {sorted(non_manifold - ACCEPTED_NON_MANIFOLD)}; "
        f"missing accepted exceptions: {sorted(ACCEPTED_NON_MANIFOLD - non_manifold)}"
    )
print(f"validated {len(paths)} URDF meshes; accepted {len(non_manifold)} non-manifold omni-wheel references")
