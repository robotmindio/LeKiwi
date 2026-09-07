"""Render the actual overlay STLs, with an exploded placement view (requires VTK)."""

import json
from pathlib import Path

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
LEVELS = {
    entry["name"]: entry["z"] for entry in json.loads((OUT / "layout.json").read_text())
}
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
