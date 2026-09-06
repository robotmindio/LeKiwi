"""Verify the installed lidar bracket uses the removed Pi's real plate holes."""

import xml.etree.ElementTree as ET
import json
from pathlib import Path
import FreeCAD as App
from scripts.cad_utils import urdf_matrix

doc = App.openDocument("cad/assembly/LeKiwi.FCStd")
links = {link.UrdfName: link for link in doc.getObject("LeKiwiLinks").Group}
assert not {"Bottom-V2-v3", "Top-V2-v2"} & links.keys()
plate_holes = []
for part in links["base_plate_layer2-v3"].CadParts:
    for wire in part.Shape.Wires:
        box = wire.BoundBox
        if box.ZLength < .001 and max(box.XLength, box.YLength) < 4:
            plate_holes.append(App.Vector((box.XMin+box.XMax)/2, (box.YMin+box.YMax)/2, 7))
robot = ET.parse("URDF/LeKiwi.urdf.xacro").getroot()
spec = json.loads(Path("cad/accessories/sensor_mount_spec.json").read_text())
mount = robot.find("joint[@name='robotskin_lidar_mount_joint']")
assert mount.find("parent").get("link") == "base_plate_layer2-v3"
pose = urdf_matrix(mount.find("origin"))
for x, y in spec["lidar"]["bracket_holes_local_mm"]:
    hole = pose.multVec(App.Vector(x, y, 0))
    assert min((hole - target).Length for target in plate_holes) < .001, hole
centre = pose.multVec(App.Vector(*(value * 1000 for value in spec["lidar"]["body_center_m"])))
assert (centre - App.Vector(*spec["lidar"]["body_center_in_plate_mm"])).Length < .001
print("lidar bracket matches all four rear plate holes, including the old Pi pair")
astra = robot.find("joint[@name='astra_pro_compact_mount_joint']")
assert astra.find("parent").get("link") == "base_plate_layer2-v3"
pose = urdf_matrix(astra.find("origin"))
first, second = spec["astra"]["plate_holes_mm"]
spacing = (App.Vector(*first) - App.Vector(*second)).Length
for x, target in zip((-spacing / 2, spacing / 2), (first, second)):
    hole = pose.multVec(App.Vector(x, 0, 0))
    assert (hole - App.Vector(*target)).Length < .001, hole
    assert min((hole - target).Length for target in plate_holes) < .001, hole
origin = [value * 1000 for value in spec["astra"]["mount_origin_m"]]
assert (pose.multVec(App.Vector()) - App.Vector(*origin)).Length < .001
print("Astra bracket matches the operator-selected left-edge plate holes")
