"""Verify the installed lidar, Astra and RPi 5 mounts use real upper-plate holes."""

import xml.etree.ElementTree as ET
import json
import sys
from pathlib import Path
import FreeCAD as App
from scripts.cad_utils import urdf_matrix

assembly = sys.argv[1] if len(sys.argv) > 1 else "cad/assembly/LeKiwi.FCStd"
generated_path = sys.argv[2] if len(sys.argv) > 2 else "URDF/LeKiwi.urdf.xacro"
doc = App.openDocument(assembly)
links = {link.UrdfName: link for link in doc.getObject("LeKiwiLinks").Group}
assert not {"Bottom-V2-v3", "Top-V2-v2"} & links.keys()
plate_holes = []
for part in links["base_plate_layer2-v3"].CadParts:
    for wire in part.Shape.Wires:
        box = wire.BoundBox
        if box.ZLength < .001 and max(box.XLength, box.YLength) < 4:
            plate_holes.append(App.Vector((box.XMin+box.XMax)/2, (box.YMin+box.YMax)/2, 7))
robot = ET.parse(generated_path).getroot()
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
plate = robot.find("joint[@name='rpi5_through_plate_joint']")
assert plate.find("parent").get("link") == "base_plate_layer2-v3"
pose = urdf_matrix(plate.find("origin"))
for x, y in spec["rpi5"]["plate_bolt_stations_mm"]:
    # 12x10 through-plate M3 stations sit on odd multiples of 5 mm.
    assert abs(x) <= 55 and abs(y) <= 45 and x % 10 == 5 and y % 10 == 5, (x, y)
    hole = pose.multVec(App.Vector(x, y, 0))
    assert min((hole - target).Length for target in plate_holes) < .001, hole
for name in ("rpi5_usb_carrier_joint", "rpi5_table_joint"):
    # Carrier (x in -45..35, y +-15) and table (+-55, +-45) locks share the
    # plate's station grid only when their frames coincide in XY.
    joint = robot.find(f"joint[@name='{name}']")
    assert joint.find("parent").get("link") == "rpi5_through_plate"
    origin = urdf_matrix(joint.find("origin"))
    assert (origin.multVec(App.Vector()) - App.Vector(0, 0, 4)).Length < .001, name
print("RPi 5 through plate bolts to upper-plate holes; carrier and table lock into it")
