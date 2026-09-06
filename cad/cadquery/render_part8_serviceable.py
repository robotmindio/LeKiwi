"""Render actual exported CAD: original, assembled redesign, and opened covers."""

from vtkmodules.vtkIOImage import vtkPNGWriter
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkTextActor,
    vtkWindowToImageFilter,
)
import vtkmodules.vtkRenderingFreeType
import vtkmodules.vtkRenderingOpenGL2

from so101_scene import wrist_scene
from test_so101_part8_serviceable import OUTPUT, read_mesh


def main():
    window = vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(1800, 900)
    meshes = {
        name: read_mesh(OUTPUT / f"{name}.stl")
        for name in ("original", "cradle", "cover_left", "cover_right")
    }
    motor = next(mesh for _, _, mesh in wrist_scene({}, {"wrist_link"}))
    for column, title in enumerate(
        (
            "Original upstream part",
            "Serviceable redesign",
            "Covers removed / servo shown",
        )
    ):
        renderer = vtkRenderer()
        renderer.SetViewport(column / 3, 0, (column + 1) / 3, 1)
        renderer.SetBackground(0.94, 0.95, 0.97)
        items = (
            [(meshes["original"], (0.65, 0.69, 0.74), 0)]
            if column == 0
            else [
                (meshes["cradle"], (0.20, 0.25, 0.30), 0),
                (meshes["cover_left"], (0.90, 0.90, 0.87), -32 if column == 2 else 0),
                (meshes["cover_right"], (0.90, 0.90, 0.87), 32 if column == 2 else 0),
            ]
        )
        if column == 2:
            items.append((motor, (0.45, 0.48, 0.52), 0))
        for mesh, color, shift in items:
            mapper = vtkPolyDataMapper()
            mapper.SetInputData(mesh)
            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.SetPosition(0, shift, 0)
            actor.GetProperty().SetColor(color)
            actor.GetProperty().SetAmbient(0.25)
            actor.GetProperty().SetDiffuse(0.75)
            renderer.AddActor(actor)
        text = vtkTextActor()
        text.SetInput(title)
        text.SetPosition(22, 28)
        text.GetTextProperty().SetFontSize(22)
        text.GetTextProperty().SetColor(0.12, 0.16, 0.20)
        renderer.AddActor2D(text)
        camera = renderer.GetActiveCamera()
        camera.SetPosition(110, -180, 95)
        camera.SetFocalPoint(4, 0, 0)
        camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn()
        camera.SetParallelScale(100 if column == 2 else 75)
        renderer.ResetCameraClippingRange()
        window.AddRenderer(renderer)
    window.Render()
    capture = vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.Update()
    writer = vtkPNGWriter()
    writer.SetFileName(str(OUTPUT / "preview.png"))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()


if __name__ == "__main__":
    main()
