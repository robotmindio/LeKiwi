"""Verify the installed lidar bracket uses the removed Pi's real plate holes."""

import xml.etree.ElementTree as ET
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
mount = robot.find("joint[@name='robotskin_lidar_mount_joint']")
assert mount.find("parent").get("link") == "base_plate_layer2-v3"
pose = urdf_matrix(mount.find("origin"))
for x in (-35, -15):
    for y in (-20, 20):
        hole = pose.multVec(App.Vector(x, y, 0))
        assert min((hole - target).Length for target in plate_holes) < .001, hole
centre = pose.multVec(App.Vector(20, -5, 12))
assert (centre - App.Vector(-5, -135, 19)).Length < .001
print("lidar bracket matches all four rear plate holes, including the old Pi pair")
