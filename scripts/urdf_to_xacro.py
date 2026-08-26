"""Create the maintained Xacro baseline from the upstream URDF export."""

import sys
from pathlib import Path


if len(sys.argv) != 3:
    raise SystemExit("usage: urdf_to_xacro.py INPUT.urdf OUTPUT.urdf.xacro")

source, output = map(Path, sys.argv[1:])
text = source.read_text()
root = '<robot name="LeKiwi">'
if root not in text:
    raise RuntimeError("expected the LeKiwi robot root element")

text = text.replace(
    root,
    '<robot xmlns:xacro="http://www.ros.org/wiki/xacro" name="LeKiwi">\n'
    '    <xacro:property name="mesh_dir" value="meshes" />',
    1,
).replace('filename="meshes/', 'filename="${mesh_dir}/')
output.write_text(text)
