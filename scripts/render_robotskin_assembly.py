"""Render the physical CAD chassis, full build and three complete wheel assemblies."""

import json
from pathlib import Path

import numpy as np
import trimesh
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
import vtkmodules.vtkRenderingFreeType  # noqa: F401 - register text renderer
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401 - register OpenGL renderer

OUT = Path(__file__).resolve().parents[1] / "cad/generated/robotskin"
SCENE = json.loads((OUT / "scene.json").read_text())
COLORS = {
    "plate": (0.68, 0.63, 0.51),
    "mount": (0.16, 0.36, 0.65),
    "motor": (0.20, 0.22, 0.26),
    "hub": (0.63, 0.28, 0.66),
    "wheel": (0.12, 0.13, 0.15),
    "arm": (0.93, 0.68, 0.14),
    "other": (0.45, 0.51, 0.54),
    "skin": (0.95, 0.60, 0.13),
    "post": (0.72, 0.51, 0.20),
}


def kind(name):
    if "Hex-Standoff" in name:
        return "post"
    if "Omni-Directional-Wheel" in name:
        return "wheel"
    if "omni_wheel_mount" in name:
        return "hub"
    if "drive_motor_mount" in name:
        return "mount"
    if "ST3215_Servo" in name:
        return "motor"
    if name.startswith("so101_"):
        return "arm"
    if "base_plate_layer" in name:
        return "plate"
    return "other"


def actor(renderer, entry, opacity=1):
    reader = vtkSTLReader()
    reader.SetFileName(str(OUT / entry["file"]))
    reader.Update()
    assert reader.GetOutput().GetNumberOfPolys(), entry
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(reader.GetOutputPort())
    item = vtkActor()
    item.SetMapper(mapper)
    item.GetProperty().SetColor(COLORS[kind(entry["name"])])
    item.GetProperty().SetOpacity(opacity)
    renderer.AddActor(item)


def label(renderer, text):
    item = vtkTextActor()
    item.SetInput(text)
    item.SetPosition(20, 20)
    item.GetTextProperty().SetFontSize(22)
    item.GetTextProperty().SetColor(0.10, 0.14, 0.18)
    renderer.AddActor2D(item)


def line(renderer, a, b, color):
    source = vtkLineSource()
    source.SetPoint1(*a)
    source.SetPoint2(*b)
    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(source.GetOutputPort())
    item = vtkActor()
    item.SetMapper(mapper)
    item.GetProperty().SetColor(color)
    item.GetProperty().SetLineWidth(3)
    renderer.AddActor(item)


def panel(window, viewport, entries, title, position, focal, scale, up=(0, 0, 1)):
    renderer = vtkRenderer()
    renderer.SetViewport(*viewport)
    renderer.SetBackground(0.96, 0.97, 0.98)
    for entry in entries:
        actor(renderer, entry)
    camera = renderer.GetActiveCamera()
    camera.SetPosition(*position)
    camera.SetFocalPoint(*focal)
    camera.SetViewUp(*up)
    camera.ParallelProjectionOn()
    if scale is None:
        renderer.ResetCamera()
        camera.SetParallelScale(camera.GetParallelScale() * 1.12)
    else:
        camera.SetParallelScale(scale)
    label(renderer, title)
    renderer.ResetCameraClippingRange()
    window.AddRenderer(renderer)
    return renderer


def save(window, name):
    window.Render()
    capture = vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.Update()
    writer = vtkPNGWriter()
    writer.SetFileName(str(OUT / name))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()


def main():
    window = vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(1600, 1000)
    panel(
        window,
        (0, 0, 0.5, 1),
        SCENE,
        "Corrected CAD: v2 cages, six pillars + SO-101\nFront oblique view",
        (450, 550, 440),
        (0, 45, 130),
        None,
    )
    panel(
        window,
        (0.5, 0, 1, 1),
        SCENE,
        "Same assembly - rear oblique view\nElectronics shown in their reference positions",
        (-450, -550, 380),
        (0, 45, 130),
        None,
    )
    save(window, "full_build.png")
    wheel_parts = [
        e for e in SCENE if kind(e["name"]) in ("wheel", "hub", "motor", "mount")
    ]
    floor = [e for e in SCENE if e["name"] == "base_plate_layer1-v5"]
    window = vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(1600, 1400)
    overview = panel(
        window,
        (0, 0.5, 0.5, 1),
        wheel_parts + floor,
        "Corrected CAD: all three v2 wheel assemblies\nGreen: radius / red: wheel-plane direction",
        (0, 0, 500),
        (0, 0, 0),
        190,
        (0, 1, 0),
    )
    checks = []
    for index, suffix in enumerate(("-2", "-1", "")):
        names = {
            "drive_motor_mount-v11" + suffix,
            "ST3215_Servo_Motor-v1" + suffix,
            "omni_wheel_mount-v5" + suffix,
            "4-Omni-Directional-Wheel_Single_Body-v1" + suffix,
        }
        group = [e for e in wheel_parts if e["name"] in names]
        assert len(group) == 4, names
        mesh = trimesh.load_mesh(
            OUT / next(e["file"] for e in group if kind(e["name"]) == "wheel")
        )
        centre = mesh.bounds.mean(axis=0)
        radial = centre.copy()
        radial[2] = 0
        radial /= np.linalg.norm(radial)
        # Physical wheel axle is the short principal axis of the complete wheel mesh.
        _, vectors = np.linalg.eigh(np.cov(mesh.vertices.T))
        axle = vectors[:, 0]
        if np.dot(axle, radial) < 0:
            axle = -axle
        angle = float(np.degrees(np.arccos(np.clip(abs(np.dot(axle, radial)), -1, 1))))
        assert angle < 1.0, (suffix, "wheel plane is not tangent to chassis", angle)
        tangent = np.cross([0, 0, 1], axle)
        tangent /= np.linalg.norm(tangent)
        c = np.r_[centre[:2], 80]
        line(overview, [0, 0, 80], c, (0.12, 0.65, 0.25))
        line(overview, c - 45 * tangent, c + 45 * tangent, (0.86, 0.16, 0.12))
        viewports = [(0.5, 0.5, 1, 1), (0, 0, 0.5, 0.5), (0.5, 0, 1, 0.5)]
        focus = np.mean(
            [trimesh.load_mesh(OUT / e["file"]).bounds.mean(axis=0) for e in group],
            axis=0,
        )
        camera = focus - 180 * radial + 80 * tangent + [0, 0, 130]
        panel(
            window,
            viewports[index],
            group,
            f"{('Back', 'Right', 'Left')[index]}: mount + motor + hub + wheel\nBlue mount / dark motor / purple hub",
            camera,
            focus,
            78,
        )
        checks.append(
            {
                "wheel": ("back", "right", "left")[index],
                "centre_mm": centre.tolist(),
                "axle": axle.tolist(),
                "axle_to_radius_degrees": angle,
            }
        )
    save(window, "wheel_assemblies.png")
    (OUT / "wheel_orientation_checks.json").write_text(
        json.dumps(checks, indent=2) + "\n"
    )
    if (
        not (OUT / "floor_installed.stl").exists()
        or (OUT / "floor_installed.stl").stat().st_mtime
        < (OUT / "layout.json").stat().st_mtime
    ):
        print("Reference renders complete; floor placement needs the rebuilt skin.")
        return
    # Show the newly fitted floor with full wheel assemblies, from both sides.
    skin = {"name": "floor_skin", "file": "floor_installed.stl"}
    COLORS["other"] = COLORS["skin"]
    window = vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(1600, 900)
    panel(
        window,
        (0, 0, 0.5, 1),
        wheel_parts + [skin],
        "Corrected floor + complete wheel assemblies\nTop view",
        (0, 0, 500),
        (0, 0, 0),
        190,
        (0, 1, 0),
    )
    panel(
        window,
        (0.5, 0, 1, 1),
        wheel_parts + [skin],
        "Corrected floor - oblique view\nFastening uses the normal RobotSkin ports",
        (350, -450, 350),
        (0, 0, 5),
        195,
    )
    save(window, "floor_wheel_fit.png")
    window = vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(1600, 900)
    upper = [e for e in SCENE if e["name"] == "base_plate_layer2-v3"]
    ceiling = [{"name": "ceiling_skin", "file": "ceiling_installed.stl"}]
    for index, (parts, title) in enumerate((
        (upper, "Upper-plate CAD: rounded cable windows"),
        (ceiling, "Ceiling skin: same installed XY coordinates"),
    )):
        panel(window, (index / 2, 0, (index + 1) / 2, 1), parts,
              title + "\n60 x 20 mm at (0, 0); 20 x 30 mm at (0, 50); R4\nPhoto-approximated dimensions",
              (0, 0, 500), (0, 0, 50), 140, (0, 1, 0))
    save(window, "upper_windows.png")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
