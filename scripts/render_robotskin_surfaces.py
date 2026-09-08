"""Render the actual overlay STLs, with an exploded placement view (requires VTK)."""

import json
from pathlib import Path

from vtkmodules.vtkFiltersSources import vtkLineSource
from vtkmodules.vtkIOGeometry import vtkSTLReader
from vtkmodules.vtkIOImage import vtkPNGWriter
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkTextActor,
    vtkWindowToImageFilter,
)
import vtkmodules.vtkRenderingFreeType  # noqa: F401 - registers text rendering
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401 - registers OpenGL renderer


OUT = Path(__file__).resolve().parents[1] / "cad/generated/robotskin"
LAYOUT = json.loads((OUT / "layout.json").read_text())
LEVELS = {entry["name"]: entry["z"] for entry in LAYOUT}
COLORS = [(0.10, 0.65, 0.70), (0.93, 0.61, 0.13), (0.43, 0.48, 0.82)]
window = vtkRenderWindow()
window.SetOffScreenRendering(1)
window.SetSize(1600, 1200)


def actor(renderer, name, color, shift=0, flip=False):
    reader = vtkSTLReader()
    reader.SetFileName(str(OUT / (name + ".stl")))
    reader.Update()
    assert reader.GetOutput().GetNumberOfPolys(), name
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(reader.GetOutputPort())
    item = vtkActor()
    item.SetMapper(mapper)
    item.SetPosition(0, 0, shift)
    if flip:
        item.RotateX(180)
    item.GetProperty().SetColor(color)
    renderer.AddActor(item)


for index, title in enumerate(
    (
        "Superior exterior",
        "Piso interior",
        "Techo interior (cara expuesta)",
        "Despiece: superior / techo / piso",
    )
):
    renderer = vtkRenderer()
    column, row = index % 2, index // 2
    renderer.SetViewport(column / 2, (1 - row) / 2, (column + 1) / 2, (2 - row) / 2)
    renderer.SetBackground(0.96, 0.97, 0.98)
    camera = renderer.GetActiveCamera()
    if index < 3:
        actor(renderer, ("top", "floor", "ceiling")[index], COLORS[index])
        camera.SetPosition(0, 0, 400)
        camera.SetFocalPoint(0, 0, 0)
        camera.SetViewUp(0, 1, 0)
        camera.ParallelProjectionOn()
        camera.SetParallelScale(135)
    else:
        for name, color, shift in zip(
            ("top", "floor", "ceiling"), COLORS, (110, 0, 55)
        ):
            actor(
                renderer,
                name,
                color,
                shift + LEVELS[name] + (4 if name == "ceiling" else 0),
                flip=name == "ceiling",
            )
        camera.SetPosition(350, -450, 390)
        camera.SetFocalPoint(0, 0, 80)
        camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn()
        camera.SetParallelScale(175)
    label = vtkTextActor()
    label.SetInput(title)
    label.SetPosition(25, 25)
    label.GetTextProperty().SetFontSize(25)
    label.GetTextProperty().SetColor(0.12, 0.16, 0.21)
    renderer.AddActor2D(label)
    renderer.ResetCameraClippingRange()
    window.AddRenderer(renderer)
window.Render()
capture = vtkWindowToImageFilter()
capture.SetInput(window)
capture.Update()
writer = vtkPNGWriter()
writer.SetFileName(str(OUT / "preview.png"))
writer.SetInputConnection(capture.GetOutputPort())
writer.Write()
print(OUT / "preview.png")

# Measured footprints, not the incompatible legacy 3D motor assemblies.
floor = next(entry for entry in LAYOUT if entry["name"] == "floor")
window = vtkRenderWindow()
window.SetOffScreenRendering(1)
window.SetSize(1100, 1100)
renderer = vtkRenderer()
renderer.SetBackground(0.96, 0.97, 0.98)
actor(renderer, "floor", COLORS[1])
for base in floor["motor_bases"]:
    points = base["footprint"]
    for a, b in zip(points, points[1:] + points[:1]):
        line = vtkLineSource()
        line.SetPoint1(*a, 5)
        line.SetPoint2(*b, 5)
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(line.GetOutputPort())
        item = vtkActor()
        item.SetMapper(mapper)
        item.GetProperty().SetColor(0.10, 0.32, 0.85)
        item.GetProperty().SetLineWidth(3)
        renderer.AddActor(item)
camera = renderer.GetActiveCamera()
camera.SetPosition(0, 0, 400)
camera.SetFocalPoint(0, 0, 0)
camera.SetViewUp(0, 1, 0)
camera.ParallelProjectionOn()
camera.SetParallelScale(135)
label = vtkTextActor()
margin = floor["motor_bases"][0]["clearance_mm"]
label.SetInput(
    "Blue: measured 50 x 37 mm bases, centered and flush with chassis flats\n"
    f"Orange: floor STL / {margin:g} mm clearance on every side\n"
    "Footprints only; not a reconstruction of the complete motor assemblies"
)
label.SetPosition(25, 20)
label.GetTextProperty().SetFontSize(21)
label.GetTextProperty().SetColor(0.12, 0.16, 0.21)
renderer.AddActor2D(label)
renderer.ResetCameraClippingRange()
window.AddRenderer(renderer)
window.Render()
capture.SetInput(window)
capture.Modified()
capture.Update()
writer.SetFileName(str(OUT / "floor_base_fit.png"))
writer.Write()
print(OUT / "floor_base_fit.png")
# This previous image asserted fit against the superseded wheel-mount geometry.
(OUT / "floor_wheel_fit.png").unlink(missing_ok=True)
