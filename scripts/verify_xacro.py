"""Check that a generated Xacro preserves the baseline URDF semantics."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


XACRO_PROPERTY = "{http://www.ros.org/wiki/xacro}property"


def normalise(element):
    if element.tag == XACRO_PROPERTY:
        return None
    attributes = dict(element.attrib)
    if element.tag == "mesh":
        attributes["filename"] = attributes["filename"].replace("${mesh_dir}/", "meshes/")
        attributes["filename"] = attributes["filename"].replace("meshes/reauthored/", "meshes/")
    children = [normalise(child) for child in element]
    return element.tag, tuple(sorted(attributes.items())), tuple(child for child in children if child is not None)


if len(sys.argv) != 3:
    raise SystemExit("usage: verify_xacro.py BASELINE.urdf GENERATED.urdf.xacro")

baseline = normalise(ET.parse(sys.argv[1]).getroot())
generated_path = Path(sys.argv[2])
generated_root = ET.parse(generated_path).getroot()
baseline_root = ET.parse(sys.argv[1]).getroot()
baseline_links = {link.get("name"): link for link in baseline_root.findall("link")}
for link in generated_root.findall("link"):
    for kind in ("visual", "collision"):
        mesh = link.find(f"{kind}/geometry/mesh")
        if mesh is not None and mesh.get("filename", "").startswith("${mesh_dir}/reauthored/"):
            origin = link.find(f"{kind}/origin")
            if origin is None or origin.get("xyz") != "0 0 0" or origin.get("rpy") != "0 0 0":
                raise SystemExit(f"{link.get('name')}: reauthored {kind} is not in the link frame")
            baseline_origin = baseline_links[link.get("name")].find(f"{kind}/origin")
            origin.attrib = dict(baseline_origin.attrib)
for mesh in generated_root.findall(".//mesh"):
    filename = mesh.get("filename", "")
    if filename.startswith("${mesh_dir}/reauthored/"):
        output = generated_path.parent / "meshes" / "reauthored" / filename.rsplit("/", 1)[1]
        if not output.is_file() or output.stat().st_size == 0:
            raise SystemExit(f"missing reauthored mesh: {output}")
generated = normalise(generated_root)
if baseline != generated:
    raise SystemExit("generated Xacro does not preserve baseline URDF semantics")
print("generated Xacro preserves baseline URDF semantics")
