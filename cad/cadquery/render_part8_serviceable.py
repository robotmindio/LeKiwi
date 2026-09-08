"""Render actual exported CAD: original, single-piece redesign, and underside."""

from vtkmodules.vtkIOImage import vtkPNGWriter
from vtkmodules.vtkFiltersCore import vtkPolyDataNormals
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkTextActor,
    vtkWindowToImageFilter,
)
import vtkmodules.vtkRenderingFreeType
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401 - registers the rendering backend

from test_so101_part8_serviceable import OUTPUT, read_mesh


def render(views, filename, columns):
    window = vtkRenderWindow()
    window.SetOffScreenRendering(1)
    rows = (len(views) + columns - 1) // columns
    window.SetSize(700 * columns, 650 * rows)
    for index, (title, name, position, focus, scale) in enumerate(views):
        column, row = index % columns, index // columns
        renderer = vtkRenderer()
        renderer.SetViewport(
            column / columns,
            1 - (row + 1) / rows,
            (column + 1) / columns,
            1 - row / rows,
        )
        renderer.SetBackground(0.94, 0.95, 0.97)
        normals = vtkPolyDataNormals()
        normals.SetInputData(read_mesh(OUTPUT / f"{name}.stl"))
        # Avoid false smoothing across the sharp mounting-hole edges.
        normals.SetFeatureAngle(30)
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(normals.GetOutputPort())
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(
            (0.65, 0.69, 0.74) if name == "original" else (0.80, 0.83, 0.86)
        )
        actor.GetProperty().SetAmbient(0.25)
        actor.GetProperty().SetDiffuse(0.75)
        actor.GetProperty().SetInterpolationToPhong()
        renderer.AddActor(actor)
        text = vtkTextActor()
        text.SetInput(title)
        text.SetPosition(22, 28)
        text.GetTextProperty().SetFontSize(22)
        text.GetTextProperty().SetColor(0.12, 0.16, 0.20)
        renderer.AddActor2D(text)
        camera = renderer.GetActiveCamera()
        camera.SetPosition(*position)
        camera.SetFocalPoint(*focus)
        camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn()
        camera.SetParallelScale(scale)
        renderer.ResetCameraClippingRange()
        window.AddRenderer(renderer)
    window.Render()
    capture = vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.Update()
    writer = vtkPNGWriter()
    writer.SetFileName(str(OUTPUT / filename))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()


def main():
    render(
        [
            ("Original upstream part", "original", (110, -180, 95), (4, 0, 0), 60),
            ("Blended single-piece cradle", "cradle", (110, -180, 95), (4, 0, 0), 60),
            ("Underside / motor access", "cradle", (110, -180, -95), (4, 0, 0), 60),
        ],
        "preview.png",
        3,
    )
    render(
        [
            ("Fork roots and deck", "cradle", (100, -160, 120), (0, 0, 12), 30),
            ("Front motor opening", "cradle", (160, -60, 25), (19, 0, -12), 35),
            ("Rear transitions", "cradle", (-140, -170, 80), (-4, 0, -5), 45),
            ("Seat and underside", "cradle", (100, -160, -120), (8, 0, -16), 33),
        ],
        "details.png",
        2,
    )


if __name__ == "__main__":
    main()
