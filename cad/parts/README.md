# Native-part migration queue

Every URDF link already has a FreeCAD source in `../assembly/LeKiwi.FCStd`; see [`../reference_mapping.json`](../reference_mapping.json) for its exact BREP or mesh reference. The queue below is only the remaining work to recreate native, constrained FreeCAD feature models. Each replacement must be in its URDF-link frame, then attached with `scripts/attach_cad_part.sh` and exported with `scripts/export_robot.sh`.

Rebuild the editable base-plate source solids from the exact laser profiles:

```sh
./scripts/build_laser_plate_sources.sh
./scripts/verify_laser_plate_sources.sh
./scripts/link_base_plate_sources.sh
./scripts/export_robot.sh
```

Open either generated `.FCStd` file in FreeCAD. Change `Extrusion.LengthFwd` for the selected stock thickness; its `LaserProfile` is the exact profile used by the DXF. The lower plate is placed from `z=-7` to `z=0` in its URDF link frame and the upper plate from `z=0` to `z=7`.

The linked plate sources already drive the Xacro visual/collision meshes. Their legacy inertial values remain active until the actual stock is known. After choosing material or measuring the finished part, activate a CAD-derived inertia explicitly; for example:

```sh
./scripts/attach_cad_part.sh cad/assembly/LeKiwi.FCStd base_plate_layer1-v5 CadBasePlateLower 1240 0
./scripts/export_robot.sh
```

Here `1240` is only an example density in kg/m³; use `0` as the final argument only when that density represents the finished part. A measured mass is the safer override for printed or assembled parts.

| Priority | Unique manufactured component | URDF links | Fusion archive reference | Status |
| --- | --- | --- | --- | --- |
| 1 | Lower base plate | `base_plate_layer1-v5` | `base_plate_layer1` | FreeCAD extrusion source available |
| 1 | Upper base plate | `base_plate_layer2-v3` | `base_plate_layer2` | FreeCAD extrusion source available |
| 2 | Drive motor mount | `drive_motor_mount-v11*` | `drive_motor_mount` | STEP BREP reference linked; native parametric source pending |
| 2 | Omni-wheel mount | `omni_wheel_mount-v5*` | `omni_wheel_mount` | Exact URDF mesh reference linked; native parametric source pending |
| 2 | Servo controller mount | `servo_controller_mount-v3` | `servo_controller_mount` | STEP BREP reference linked; native parametric source pending |
| 2 | LiPo battery mount | `lipo_battery_mount-v3` | `lipo_battery_mount` | STEP BREP reference linked; native parametric source pending |
| 3 | Base camera mount | `Camera-Mount-v8` | `Camera Mount` | STEP BREP reference linked; native parametric source pending |
| 3 | Wrist camera mount | `Wrist-Camera-Mount-v11` | `wrist_camera_mount` | STEP BREP reference linked; native parametric source pending |

The Fusion archive embeds the listed proprietary `.f3d` component files, but their feature timelines have no reliable open-source importer. The STEP assembly and matching STL files are the dimensional reference for each FreeCAD reconstruction.

The SO-100/SO-101 arm, wheels, motors, standoffs, battery, and cameras are purchased or separately maintained designs. Keep them as measured/vendor solids and use mass overrides instead of reverse-engineering them into LeKiwi-specific sources.
