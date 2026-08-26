# Native LeKiwi part sources

All LeKiwi-specific manufactured parts represented by the URDF assembly now have editable FreeCAD sources. `LeKiwi.FCStd` links each source's `Final` feature into the appropriate URDF link, so mesh and Xacro regeneration is deterministic.

| Manufactured component | Source file | URDF links | Status |
| --- | --- | --- | --- |
| Lower base plate | `base_plate_lower.FCStd` | `base_plate_layer1-v5` | Laser-profile extrusion |
| Upper base plate | `base_plate_upper.FCStd` | `base_plate_layer2-v3` | Laser-profile extrusion |
| Drive motor mount | `drive_motor_mount.FCStd` | `drive_motor_mount-v11*` | Native parametric source |
| Omni-wheel mount | `omni_wheel_mount.FCStd` | `omni_wheel_mount-v5*` | Native parametric source |
| Servo controller mount | `servo_controller_mount.FCStd` | `servo_controller_mount-v3` | Native parametric source |
| LiPo battery mount | `lipo_battery_mount.FCStd` | `lipo_battery_mount-v3` | Native parametric source |
| Base camera mount | `base_camera_mount.FCStd` | `Camera-Mount-v8` | Native parametric source |
| Wrist camera mount | `wrist_camera_mount.FCStd` | `Wrist-Camera-Mount-v11` | Native parametric source |

Open a source file in FreeCAD and edit its `Parameters` object or its named profile/Part features. Save it, then run:

```sh
./scripts/link_native_part_sources.sh
./scripts/export_robot.sh
./scripts/verify_native_part_sources.sh
```

The first script replaces only the managed native `CadParts` links and verifies their bounding boxes and volumes against the baseline. It leaves `UseCadMass=False`; set an actual printed mass or density with `attach_cad_part.sh` before asking the Xacro exporter to calculate inertia.

To recreate the initial six models from the reference STEP and canonical STL files, run:

```sh
./scripts/build_native_part_sources.sh
./scripts/link_native_part_sources.sh
./scripts/export_robot.sh
./scripts/verify_native_part_sources.sh
```

The builder overwrites these six `.FCStd` files. It is a reset tool, not a save operation for manual changes.

The source models use independent FreeCAD profile features and standard Part operations; none embeds an external mesh or BREP as its final solid. The wrist-camera mount keeps one hidden `InterfaceClearance` BREP cut tool derived from the Fusion XRef it must fit; its surrounding body, plate, bosses, and holes remain native FreeCAD features. Their dimensional starting points came from the Fusion STEP export, except the omni-wheel mount, whose canonical URDF STL revision is the authoritative geometry. The Fusion archive embeds proprietary `.f3d` files, but its timeline has no reliable open-source importer.

`verify_native_part_sources.sh` checks the native feature-tree contract and the
2% bounds/volume placement tolerance. It is not a surface-equivalence test.
Run `./scripts/compare_reauthored_assets.sh` for the stricter bidirectional
mesh audit. The checked-in report passes all twelve native link instances,
with no more than 0.056 mm maximum or 0.034 mm 95th-percentile sampled
surface deviation from the original URDF assets.

Purchased or separately maintained designs, and optional accessory prints outside this URDF assembly, remain measured/vendor references rather than reverse-engineered LeKiwi-specific source models.
