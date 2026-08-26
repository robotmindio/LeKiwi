"""Check that a generated Xacro preserves the baseline URDF semantics."""

import sys
import xml.etree.ElementTree as ET


XACRO_PROPERTY = "{http://www.ros.org/wiki/xacro}property"


def normalise(element):
    if element.tag == XACRO_PROPERTY:
        return None
    attributes = dict(element.attrib)
    if element.tag == "mesh":
        attributes["filename"] = attributes["filename"].replace("${mesh_dir}/", "meshes/")
    children = [normalise(child) for child in element]
    return element.tag, tuple(sorted(attributes.items())), tuple(child for child in children if child is not None)


if len(sys.argv) != 3:
    raise SystemExit("usage: verify_xacro.py BASELINE.urdf GENERATED.urdf.xacro")

baseline = normalise(ET.parse(sys.argv[1]).getroot())
generated = normalise(ET.parse(sys.argv[2]).getroot())
if baseline != generated:
    raise SystemExit("generated Xacro does not preserve baseline URDF semantics")
print("generated Xacro preserves baseline URDF semantics")
