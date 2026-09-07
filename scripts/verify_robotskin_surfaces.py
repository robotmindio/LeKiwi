"""Check the three print meshes against their measured, collision-checked layouts."""

import json
import math
from pathlib import Path
import sys

import numpy as np
import shapely
from shapely.geometry import Polygon
import trimesh

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True  # Keep imports from dirtying the pinned submodule.
sys.path.insert(0, str(ROOT / "cad/upstream/RobotSkin/scripts"))
from validate_stl import validate  # noqa: E402 - reuse pinned RobotSkin mesh checks

OUT = ROOT / "cad/generated/robotskin"
for entry in json.loads((OUT / "layout.json").read_text()):
    name = entry["name"]
    path = OUT / (name + ".stl")
    assert not (errors := validate(path)), (name, errors)
    mesh = trimesh.load_mesh(path)
    assert np.allclose(mesh.bounds[:, 2], [0, 4], atol=0.001), name
    region = Polygon(entry["outline"]).buffer(-0.5, join_style="mitre")
    for cut in entry["cuts"]:
        region = region.difference(Polygon(cut))
    for x, y, radius in entry["posts"]:
        region = region.difference(
            Polygon(
                [
                    (
                        x + radius * math.cos(i * math.tau / 32),
                        y + radius * math.sin(i * math.tau / 32),
                    )
                    for i in range(32)
                ]
            )
        )
    assert region.is_valid and region.geom_type == "Polygon", name
    xy = mesh.vertices[:, :2].copy()
    if name == "ceiling":
        xy[:, 1] *= -1
    # STL ASCII rounding is below 0.002 mm; preserve the measured clearances.
    allowed = region.buffer(0.002)
    shapely.prepare(allowed)
    assert shapely.covers(allowed, shapely.points(xy)).all(), name
    # Also reject triangles bridging a reserved hole even if their corners fit.
    triangles = shapely.polygons(xy[mesh.faces])
    nonflat = shapely.area(triangles) > 1e-8
    assert shapely.covers(allowed, triangles[nonflat]).all(), name
    assert not shapely.covers(allowed, shapely.points([[1000, 1000]])).any()
    print(
        f"PASS {name}: closed, connected, 4 mm thick; vertices and faces within envelope"
    )
