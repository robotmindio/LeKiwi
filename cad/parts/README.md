# Native-part migration queue

Each replacement must be a FreeCAD parametric source in this directory, copied or linked into `../assembly/LeKiwi.FCStd` in its URDF-link frame. Then attach it with `scripts/attach_cad_part.sh` and run `scripts/export_robot.sh`.

| Priority | Unique manufactured component | URDF links | Fusion archive reference | Status |
| --- | --- | --- | --- | --- |
| 1 | Lower base plate | `base_plate_layer1-v5` | `base_plate_layer1` | Exact laser DXF available; parametric FreeCAD source pending |
| 1 | Upper base plate | `base_plate_layer2-v3` | `base_plate_layer2` | Exact laser DXF available; parametric FreeCAD source pending |
| 2 | Drive motor mount | `drive_motor_mount-v11*` | `drive_motor_mount` | Pending |
| 2 | Omni-wheel mount | `omni_wheel_mount-v5*` | `omni_wheel_mount` | Pending |
| 2 | Servo controller mount | `servo_controller_mount-v3` | `servo_controller_mount` | Pending |
| 2 | LiPo battery mount | `lipo_battery_mount-v3` | `lipo_battery_mount` | Pending |
| 3 | Base camera mount | `Camera-Mount-v8` | `Camera Mount` | Pending |
| 3 | Wrist camera mount | `Wrist-Camera-Mount-v11` | `wrist_camera_mount` | Pending |

The Fusion archive embeds the listed proprietary `.f3d` component files, but their feature timelines have no reliable open-source importer. The STEP assembly and matching STL files are the dimensional reference for each FreeCAD reconstruction.

The SO-100/SO-101 arm, wheels, motors, standoffs, battery, and cameras are purchased or separately maintained designs. Keep them as measured/vendor solids and use mass overrides instead of reverse-engineering them into LeKiwi-specific sources.
