# Open CAD migration

`assembly/LeKiwi_reference.FCStd` is the complete Fusion STEP export imported into FreeCAD. It is the dimensional reference; STEP cannot retain Fusion sketches or its feature timeline.

`assembly/LeKiwi.FCStd` is the open CAD-to-ROS source. Its active `CadParts` cover all 47 URDF links:

- 2 editable FreeCAD laser-cut extrusions;
- 10 links driven by 6 native parametric FreeCAD printed-part sources;
- 23 STEP BREP references; and
- 10 canonical URDF mesh references where the STEP and URDF exports differ by more than 2%; and
- the RobotSkin LD06 base plus lidar body.

The exact source and validation result for every upstream link is recorded in [reference_mapping.json](reference_mapping.json). The RobotSkin LD06 body is authored directly in `LeKiwi.FCStd`; its mount is regenerated from the pinned [RobotSkin OpenSCAD source](upstream/RobotSkin/scad/parts/lekiwi-lidar-base.scad) before every export. The hidden `LeKiwiReferenceParts` group is retained only for placement and validation; it is not the geometry exported for a reauthored part.

## Arm source

The upstream [SO-ARM100](upstream/SO-ARM100/) repository is a pinned Git submodule at
commit `7629d2ad9853d10fb903093a33ef6114099d97e5` under its Apache-2.0 license. Its
`STEP/SO100/` directory is the editable BREP source for the SO-100 follower arm
represented by the current LeKiwi CAD and URDF; it includes the follower assembly
and individual arm parts. It is intentionally not re-exported as STL-only copies.

Initialize it after cloning, then check the expected source bundle:

```sh
git submodule update --init --recursive
./scripts/verify_arm_sources.sh
```

The LeKiwi-specific `modified_base_arm` remains a separate print: it is not
asserted to match an upstream SO-ARM100 component. The webcam gripper insert has
an editable derivative in [accessories/](accessories/README.md).

## Link identifiers

Names such as `ST3215_Servo_Motor-v1-1` and
`4-Omni-Directional-Wheel_Single_Body-v1-2` are unique Fusion-assembly
occurrence identifiers, not a sequence of part revisions. Each needs its own
URDF link and pose even when the physical component is the same. Do not delete
or merge them merely because their filenames share a `-1` or `-2` suffix.

## RobotSkin source

`upstream/RobotSkin/` is pinned at commit `b028a962e99f8a84eaebfe314e63373a82edc8c1`.
Its `scad/parts/lekiwi-lidar-base.scad` entry point and shared
`scad/lib/robotskin.scad` implementation generate the lidar mount. The generated
mesh lives under ignored `cad/generated/`; `export_robot.sh` rebuilds it and updates
the assembly before writing the URDF meshes and Xacro.

## Native printed-part sources

The complete LeKiwi-specific manufactured set represented by the URDF is editable in [parts/](parts/README.md): the two laser-cut plates plus `drive_motor_mount.FCStd`, `omni_wheel_mount.FCStd`, `servo_controller_mount.FCStd`, `lipo_battery_mount.FCStd`, `base_camera_mount.FCStd`, and `wrist_camera_mount.FCStd`.

Each printed-part file has an `Editable dimensions` (`Parameters`) object and a normal FreeCAD feature tree ending in `Final`; it contains profile features, Part extrusions, primitives, fuses, and cuts—not an imported mesh or opaque BREP wrapper. Open a source file in FreeCAD, change a parameter or profile feature, and save it. Then relink and regenerate:

```sh
./scripts/link_native_part_sources.sh
./scripts/export_robot.sh
./scripts/verify_native_part_sources.sh
```

`build_native_part_sources.sh` reconstructs the six initial source files from the validated STEP/STL references. It intentionally overwrites those source files, so use it to reset or regenerate a baseline, not after manual edits you intend to keep.

Five models preserve their STEP component frame and are placed into the URDF link frame by `link_native_part_sources.sh`. The omni-wheel source uses the canonical URDF mesh frame because its Fusion STEP revision does not match the shipped URDF mesh; its editable sectional profiles are derived once from canonical STL slices and then built as normal FreeCAD features. The linker's validation must remain below the 2% geometry tolerance before it saves the assembly.

Published, non-URDF accessory sources live in [accessories/](accessories/README.md). At present, the two webcam mounts have exact LeKiwi STEP sources and are imported as editable BREP documents; their source files are not duplicated or hand-recreated.

## Deterministic build

After changing a source or robot metadata, run:

```sh
./scripts/verify_robot.sh
```

`export_robot.sh` exports all 47 link sources to `URDF/meshes/reauthored/` and writes the complete Xacro. There is no hand-edited Xacro step. `verify_cad_migration.sh` checks the baseline migration against the original URDF and is expected to fail after an intentional geometric redesign.

`native_parts.json` is the source of truth for the six parametric printed-part documents, their assembly links, and their placement references.

For a stricter shape-fidelity audit, run:

```sh
./scripts/compare_reauthored_assets.sh
```

It compares each native FreeCAD export with its original URDF mesh using
bidirectional sampled surface distance. Add `--strict` to fail on more than
0.25 mm maximum or 0.10 mm 95th-percentile deviation. The checked-in baseline
passes all twelve native links, at 0.056 mm maximum and 0.034 mm p95 or
better; this remains separate from the older bounding-box and volume check.

## Mass and inertia

Native source links deliberately keep `UseCadMass=False` until a real material density or printed mass is known. After choosing material or measuring a finished part, activate CAD-derived mass, centre of mass, and the full inertia tensor for the relevant assembly link:

```sh
./scripts/attach_cad_part.sh cad/assembly/LeKiwi.FCStd drive_motor_mount-v11-2 CadDriveMotorMountV11_2 1240 0
./scripts/export_robot.sh
```

Here `1240` is only an example density in kg/m³. Use a measured printed mass instead of `0` for FDM or assembled parts; it accounts for infill, walls, and hardware. The exporter combines all solid CAD parts in a link with the parallel-axis theorem. Purchased components should use measured or vendor mass overrides.

The joint names, parents, children, axes, origins, and limits are editable properties in the `LeKiwiJoints` group. Together with the link source geometry, this is the deterministic Xacro contract.

## Rebuild after replacing the Fusion STEP export

```sh
./scripts/import_step_reference.sh
./scripts/seed_robot_metadata.sh
./scripts/build_laser_plate_sources.sh
./scripts/verify_laser_plate_sources.sh
./scripts/build_native_part_sources.sh
./scripts/migrate_reference_links.sh --apply
./scripts/link_base_plate_sources.sh
./scripts/link_native_part_sources.sh
./scripts/migrate_reference_links.sh --apply
./scripts/export_robot.sh
./scripts/verify_native_part_sources.sh
```

The first migration pass creates hidden placement references. The second records the validated native sources after they have been linked.
