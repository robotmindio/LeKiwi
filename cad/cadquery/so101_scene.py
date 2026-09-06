"""Pinned URDF geometry and poses for CAD clearance checks (millimetres)."""

from functools import lru_cache
from math import degrees
from pathlib import Path
import xml.etree.ElementTree as ET

import cadquery as cq
from vtkmodules.vtkCommonMath import vtkMatrix4x4
from vtkmodules.vtkCommonTransforms import vtkTransform
from vtkmodules.vtkFiltersGeneral import vtkTransformPolyDataFilter
from vtkmodules.vtkIOGeometry import vtkSTLReader


SOURCE = Path(__file__).resolve().parents[1] / "upstream/SO-ARM100/Simulation/SO101"
URDF = SOURCE / "so101_new_calib.urdf"


def origin(element: ET.Element | None) -> cq.Location:
    if element is None:
        return cq.Location()
    xyz = tuple(float(v) * 1000 for v in element.get("xyz", "0 0 0").split())
    rpy = tuple(float(v) for v in element.get("rpy", "0 0 0").split())
    pose = cq.Location(xyz)
    for axis, angle in zip(((0, 0, 1), (0, 1, 0), (1, 0, 0)), reversed(rpy)):
        pose = pose * cq.Location((0, 0, 0), axis, degrees(angle))
    return pose


def transform_mesh(mesh, pose: cq.Location):
    matrix = vtkMatrix4x4()
    trsf = pose.wrapped.Transformation()
    for row in range(3):
        for col in range(4):
            matrix.SetElement(row, col, trsf.Value(row + 1, col + 1))
    transform = vtkTransform()
    transform.SetMatrix(matrix)
    moved = vtkTransformPolyDataFilter()
    moved.SetInputData(mesh)
    moved.SetTransform(transform)
    moved.Update()
    return moved.GetOutput()


@lru_cache(maxsize=1)
def reference():
    robot = ET.parse(URDF).getroot()
    visuals = []
    for link in robot.findall("link"):
        for visual in link.findall("visual"):
            mesh = visual.find("geometry/mesh")
            if mesh is None:
                continue
            reader = vtkSTLReader()
            path = SOURCE / mesh.attrib["filename"]
            reader.SetFileName(str(path))
            reader.Update()
            if not reader.GetOutput().GetNumberOfPolys():
                raise ValueError(f"empty or missing mesh: {path}")
            scale = vtkTransform()
            scale.Scale(1000, 1000, 1000)
            scaled = vtkTransformPolyDataFilter()
            scaled.SetInputConnection(reader.GetOutputPort())
            scaled.SetTransform(scale)
            scaled.Update()
            visuals.append(
                (
                    link.attrib["name"],
                    path.stem,
                    origin(visual.find("origin")),
                    scaled.GetOutput(),
                )
            )
    return robot, visuals


def placements(angles: dict[str, float]) -> dict[str, cq.Location]:
    """Resolve the existing URDF tree without changing any joint datum or limit."""
    robot, _ = reference()
    pending = list(robot.findall("joint"))
    frames = {"base_link": cq.Location()}
    while pending:
        ready = [
            joint for joint in pending if joint.find("parent").attrib["link"] in frames
        ]
        if not ready:
            raise ValueError("URDF joint tree is disconnected or cyclic")
        for joint in ready:
            parent = frames[joint.find("parent").attrib["link"]]
            local = origin(joint.find("origin"))
            if joint.attrib["type"] != "fixed":
                angle = angles.get(joint.attrib["name"], 0.0)
                axis = tuple(float(v) for v in joint.find("axis").attrib["xyz"].split())
                local = local * cq.Location((0, 0, 0), axis, degrees(angle))
            frames[joint.find("child").attrib["link"]] = parent * local
            pending.remove(joint)
    return frames


def wrist_scene(angles: dict[str, float], links: set[str] | None = None):
    """Yield actual robot visuals in the part 8 CAD frame at the requested pose."""
    _, visuals = reference()
    frames = placements(angles)
    part_pose = next(
        pose for link, name, pose, _ in visuals if name == "wrist_roll_pitch_so101_v2"
    )
    anchor = (frames["wrist_link"] * part_pose).inverse
    for link, name, pose, mesh in visuals:
        if name == "wrist_roll_pitch_so101_v2" or (
            links is not None and link not in links
        ):
            continue
        yield link, name, transform_mesh(mesh, anchor * frames[link] * pose)
