"""Render two STL files at matching scales: python render_stl_comparison.py a.stl b.stl out.png."""

import argparse

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
import vtkmodules.vtkRenderingFreeType
import vtkmodules.vtkRenderingOpenGL2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original")
    parser.add_argument("simplified")
    parser.add_argument("output")
    args = parser.parse_args()
    window = vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(1400, 1100)
    readers = []
    for path in (args.original, args.simplified):
        reader = vtkSTLReader()
        reader.SetFileName(path)
        reader.Update()
        if not reader.GetOutput().GetNumberOfPolys():
            raise ValueError(f"empty or unreadable mesh: {path}")
        readers.append(reader)
    for row in range(2):
        for column, reader in enumerate(readers):
            renderer = vtkRenderer()
            renderer.SetViewport(
                column / 2, (1 - row) / 2, (column + 1) / 2, (2 - row) / 2
            )
            renderer.SetBackground(0.96, 0.96, 0.96)
            mapper = vtkPolyDataMapper()
            mapper.SetInputConnection(reader.GetOutputPort())
            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(
                (0.83, 0.65, 0.22) if column == 0 else (0.22, 0.55, 0.75)
            )
            renderer.AddActor(actor)
            label = vtkTextActor()
            label.SetInput(
                ("Original" if column == 0 else "Simplified")
                + (" — lower shell" if row else "")
            )
            label.SetPosition(20, 20)
            label.GetTextProperty().SetFontSize(23)
            label.GetTextProperty().SetColor(0.15, 0.15, 0.15)
            renderer.AddActor2D(label)
            camera = renderer.GetActiveCamera()
            camera.SetPosition((0, -200, -18) if row else (110, -160, 100))
            camera.SetFocalPoint((-4, 0, -18) if row else (4, 0, 0))
            camera.SetViewUp(0, 0, 1)
            camera.ParallelProjectionOn()
            camera.SetParallelScale(21 if row else 46)
            renderer.ResetCameraClippingRange()
            window.AddRenderer(renderer)
    window.Render()
    capture = vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.Update()
    writer = vtkPNGWriter()
    writer.SetFileName(args.output)
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()


if __name__ == "__main__":
    main()
