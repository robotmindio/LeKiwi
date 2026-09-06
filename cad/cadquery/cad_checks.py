"""Shared solid comparison and checked STL export, in model units (mm here)."""

from pathlib import Path

import cadquery as cq
from vtkmodules.vtkFiltersCore import (
    vtkFeatureEdges,
    vtkMassProperties,
    vtkPolyDataConnectivityFilter,
)
from vtkmodules.vtkIOGeometry import vtkSTLReader, vtkSTLWriter


def solid_delta(original: cq.Shape, candidate: cq.Shape) -> tuple[cq.Shape, cq.Shape]:
    """Return removed and added solids; never accept an invalid boolean result.

    Build the candidate from this same original object. Independently imported
    coincident spline faces can make OCCT return invalid boolean differences.
    """
    for shape in (original, candidate):
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError("comparison requires two valid single solids")
    removed, added = original.cut(candidate), candidate.cut(original)
    if not removed.isValid() or not added.isValid():
        raise ValueError("invalid CAD difference; no equivalence claim is possible")
    # Spline integration differs slightly after face splitting. This checks
    # accounting, not shape equality; callers must inspect both differences.
    error = original.Volume() + added.Volume() - candidate.Volume() - removed.Volume()
    if abs(error) > 1.0:
        raise ValueError(f"inconsistent CAD volume accounting: {error:.6f} mm³")
    return removed, added


def export_stl(shape: cq.Shape, path: Path) -> dict:
    """Export at 0.02 mm deflection and reject open/disconnected meshes.

    vtkSTLReader discards zero-area facets produced by binary STL rounding.
    No holes are filled and no surface is smoothed or remeshed.
    """
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError("STL export requires one valid solid")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not shape.exportStl(
        str(path), tolerance=0.02, angularTolerance=0.2, relative=False
    ):
        raise RuntimeError(f"failed to export {path}")
    reader = vtkSTLReader()
    reader.SetFileName(str(path))
    reader.Update()
    edges = vtkFeatureEdges()
    edges.SetInputConnection(reader.GetOutputPort())
    edges.BoundaryEdgesOn()
    edges.NonManifoldEdgesOn()
    edges.FeatureEdgesOff()
    edges.ManifoldEdgesOff()
    edges.Update()
    regions = vtkPolyDataConnectivityFilter()
    regions.SetInputConnection(reader.GetOutputPort())
    regions.SetExtractionModeToAllRegions()
    regions.Update()
    mass = vtkMassProperties()
    mass.SetInputConnection(reader.GetOutputPort())
    mass.Update()
    if (
        edges.GetOutput().GetNumberOfCells()
        or regions.GetNumberOfExtractedRegions() != 1
    ):
        raise ValueError(f"{path}: STL is open, non-manifold or disconnected")
    if abs(mass.GetVolume() / shape.Volume() - 1) > 0.001:
        raise ValueError(f"{path}: STL volume differs from CAD by more than 0.1%")
    writer = vtkSTLWriter()
    writer.SetInputData(reader.GetOutput())
    writer.SetFileName(str(path))
    writer.SetFileTypeToBinary()
    if not writer.Write():
        raise RuntimeError(f"failed to write checked STL {path}")
    return {
        "triangles": reader.GetOutput().GetNumberOfPolys(),
        "closed_manifold": True,
        "components": regions.GetNumberOfExtractedRegions(),
        "volume_mm3": mass.GetVolume(),
    }
