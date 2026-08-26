"""Attach one link-local CAD solid to a LeKiwi link and configure its mass."""

import sys
from pathlib import Path

import FreeCAD as App


if len(sys.argv) != 6:
    raise SystemExit("usage: attach_cad_part.py ASSEMBLY.FCStd LINK PART DENSITY_KG_M3 MASS_OVERRIDE_KG")

source = Path(sys.argv[1])
link_name, part_name = sys.argv[2:4]
density, mass_override = map(float, sys.argv[4:6])
if density <= 0 or mass_override < 0:
    raise SystemExit("density must be positive and mass override must be zero or positive")

document = App.openDocument(str(source))
links = document.getObject("LeKiwiLinks")
if not links:
    raise RuntimeError("missing LeKiwi robot metadata; run seed_robot_metadata.sh first")
link = next((item for item in links.Group if item.UrdfName == link_name), None)
if not link:
    raise RuntimeError(f"unknown URDF link: {link_name}")
part = document.getObject(part_name)
if not part:
    matches = [item for item in document.Objects if item.Label == part_name]
    if len(matches) != 1:
        raise RuntimeError(f"part must be an object name or a unique label: {part_name}")
    part = matches[0]
if not hasattr(part, "Shape") or part.Shape.isNull() or part.Shape.Volume <= 0:
    raise RuntimeError(f"{part.Label} is not a solid CAD part")
for property_name in ("MaterialDensity", "MassOverride"):
    if not hasattr(part, property_name):
        part.addProperty("App::PropertyFloat", property_name, "Mass")
part.MaterialDensity = density
part.MassOverride = mass_override
if part not in link.CadParts:
    link.CadParts = list(link.CadParts) + [part]
link.UseCadMass = True
document.recompute()
document.save()
print(f"attached {part.Label} to {link_name}")
