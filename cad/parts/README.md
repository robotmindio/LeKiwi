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
mesh audit. The checked-in report passes all eleven active native link instances
against the configured STEP/STL references, including the user-selected v2 cage.
The v2 rebuild's sampled deviation is 0.211 mm maximum and 0.041 mm p95;
the audit limits are 0.25 mm maximum and 0.10 mm p95.

The drive-motor source now follows `3DPrintMeshes/drive_motor_mount_v2.stl`
(SHA256 `9ad701cf2c012c735edac7867db5e3b8f24142a89b58cb0f7729b1d9a2c9615b`).
Installed dimensions are 47.5 × 34.8 × 45.5 mm; native structural extrusions,
mounting holes, counterbores and editable vent profiles replace the old tray.
Only the small vent chamfers use 0.1 mm stepped sections.
Rebuild just this source with `run_freecad_script.sh scripts/build_drive_motor_mount_v2.py`,
then link it and run `run_freecad_script.sh scripts/install_wheel_mount_v2.py --apply`.
The installer checks all twelve chassis bolt axes and preserves complete wheel units.
RobotSkin adds 4 mm per-side clearance; it does not enlarge the mount itself.

Purchased or separately maintained designs, and optional accessory prints outside this URDF assembly, remain measured/vendor references rather than reverse-engineered LeKiwi-specific source models.

The upper plate includes two photo-approximated rounded cable windows (R4):
60 × 20 mm at (0, 0) and 20 × 30 mm at (0, 50), in chassis millimetres.
`scripts/upper_plate_windows.py` replaces the original single opening while
preserving the perimeter and remaining screw holes. The plate builder applies
this correction after importing the historical DXF; that DXF remains unchanged.
RobotSkin reads the resulting CAD contours for both upper overlays.
