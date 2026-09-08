# Open CAD migration

`assembly/LeKiwi_reference.FCStd` is the complete Fusion STEP export imported into FreeCAD. It is the dimensional reference; STEP cannot retain Fusion sketches or its feature timeline.

`assembly/LeKiwi.FCStd` is the open CAD-to-ROS source for the chassis and accessories. Its active `CadParts` retain the 47-link reference assembly:

- 2 editable FreeCAD laser-cut extrusions;
- 10 links driven by 6 native parametric FreeCAD printed-part sources;
- 23 STEP BREP references; and
- 10 canonical URDF mesh references where the STEP and URDF exports differ by more than 2%; and
- the RobotSkin LD06 base plus lidar body and compact Astra Pro mount.

The final 36-link Xacro replaces that reference assembly's legacy arm subtree with the pinned SO-101 model described below and omits the removed Pi case. The exact source and validation result for every retained CAD link is recorded in [reference_mapping.json](reference_mapping.json). The RobotSkin LD06 body is authored directly in `LeKiwi.FCStd`; its mount and the compact Astra mount are regenerated from their OpenSCAD sources before every export. The hidden `LeKiwiReferenceParts` group is retained only for placement and validation; it is not the geometry exported for a reauthored part.

## Arm source

The upstream [SO-ARM100](upstream/SO-ARM100/) repository is a pinned Git submodule at
commit `7629d2ad9853d10fb903093a33ef6114099d97e5` under its Apache-2.0 license. The
final URDF and Xacro use its official `Simulation/SO101/so101_new_calib.urdf`
follower model and meshes. `scripts/replace_arm_with_so101.py` performs the one
deterministic integration step: it prefixes the arm links to avoid the ROS
`base_link`, preserves the official inertias, axes, origins, and limits, and maps
the six joints onto LeRobot's stable `arm_*` names.

`cadquery/so101_wrist.py` loads the official STEP geometry for the follower wrist
motor holder and roll carrier. Part 8, the wrist-flex body, is rebuilt from native
CadQuery sketches and features in `cadquery/so101_part8.py`; the STEP remains only
the dimensional reference. Run `python cad/cadquery/test_so101_wrist.py` with
CadQuery installed to check the native solid and the unchanged reference parts.

The export uses that native part 8 as `meshes/so101/native_wrist_flex.stl`, in
the official wrist mesh frame and converted from millimetres to metres.
All other arm meshes are refreshed from the pinned upstream source on every
export. `export_robot.sh` requires CadQuery; set `CADQUERY_PYTHON` to the Python
executable of an existing CadQuery environment if it is not installed in the
default interpreter. `verify_robot.sh` runs its STEP-fidelity check first.
The complete export also records `URDF/model-manifest.json`. Run
`python3 scripts/model_manifest.py --check` to detect source or output changes
since the last export; the ROS vendor script runs this check before copying.

The SO-101 base placement is derived from the original assembly's shoulder-pan
datum, not copied from the legacy base-part origin. The importer composes the
CAD joint chain and preserves the shoulder centre and bending plane, then
turns the installed SO-101 outward toward CAD +Y (ROS +X), the arm/fixed-camera
side confirmed by the operator. This half-turn is not a calibration offset.
The pan-frame orientations themselves differ between SO-100 and SO-101;
copying their orientations turns the arm's bending plane by a quarter turn.
Moving that datum in the assembly therefore moves the exported arm correctly.
Both sensor brackets attach to the upper plate's top surface at local z=7 mm.
The lidar reuses the removed Pi case's screw pair at x=+/-20, y=-100 mm,
plus the corresponding y=-80 mm row. Its bracket faces rearward; the lidar
centre is x=-5, y=-135 mm. `verify_sensor_mounts.py` checks all four fasteners
against the actual upper-plate contours. The historical Pi case mounting
datum is retained in `URDF/LeKiwi.urdf`, not as installed case geometry.
The Astra uses the diagonal pair nearest the operator's two fingernails:
CAD (-100, -20) and (-80, -60) mm, separated by sqrt(2000) = 44.721 mm.
Its bracket centre is (-90, -40, 7) mm and its local yaw is 116.565 degrees,
26.565 degrees counterclockwise from the previous left-facing placement.
The camera faces outward left/rear, retaining the 8-degree downward pitch.

Initialize it after cloning, then check the expected source bundle:

```sh
git submodule update --init --recursive
./scripts/verify_arm_sources.sh
```

The LeKiwi-specific `modified_base_arm` and legacy webcam gripper insert remain
separate prints; they are not part of the SO-101 robot description.

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

Four models preserve their STEP component frame. The omni-wheel source uses the canonical URDF mesh frame; the drive-motor source uses the user-selected `3DPrintMeshes/drive_motor_mount_v2.stl` frame. Both use editable native features derived from STL sections. The linker's validation must remain below the 2% geometry tolerance before it saves the assembly.

The v2 motor cages measure 47.5 × 34.8 × 45.5 mm installed. Their three placements
are aligned to the existing chassis bolt holes, 1.25 mm inset from the flats.
`scripts/install_wheel_mount_v2.py --apply` updates the six cage/servo joint poses,
the visible complete wheel units and `wheel_mount_v2_poses.json`; without `--apply`
it checks the installation. Six rods occupy (±100, 0) and (±60, ±80) mm.
RobotSkin uses 4 mm per-side wheel-unit clearance from this corrected geometry.

Published, non-URDF accessory sources live in [accessories/](accessories/README.md). At present, the two webcam mounts have exact LeKiwi STEP sources and are imported as editable BREP documents; their source files are not duplicated or hand-recreated.

## Deterministic build

After changing a source or robot metadata, run:

```sh
./scripts/verify_robot.sh
```

The verifier generates the assembly, meshes, and Xacro under a temporary build
directory and removes it when finished, so checking the model does not rewrite
the source tree. Run `export_robot.sh` when the validated generated files should
be promoted into `URDF/`. It exports the FreeCAD link sources to
`URDF/meshes/reauthored/`, replaces the legacy arm subtree with the pinned
SO-101 follower, and writes the complete Xacro. There is no hand-edited Xacro
step. `verify_cad_migration.sh` checks every retained CAD link against the
baseline URDF; the SO-101 links remain verified directly against their pinned
upstream source.

The slower reconstruction of legacy and recovery manufacturing files is a
separate audit because those files do not feed the robot Xacro:

```sh
./scripts/verify_manufacturing.sh
```

`native_parts.json` is the source of truth for the six parametric printed-part documents, their assembly links, and their placement references.

For a stricter shape-fidelity audit, run:

```sh
./scripts/compare_reauthored_assets.sh
```

It compares each native FreeCAD export with its configured reference mesh using
bidirectional sampled surface distance. Add `--strict` to fail on more than
0.25 mm maximum or 0.10 mm 95th-percentile deviation. The checked-in baseline
uses the v2 STL for all three motor cages (0.211 mm maximum, 0.041 mm p95
sampled deviation); this remains separate from the older bounding-box and volume check.

## Mass and inertia

Native source links deliberately keep `UseCadMass=False` until a real material density or printed mass is known. After choosing material or measuring a finished part, activate CAD-derived mass, centre of mass, and the full inertia tensor for the relevant assembly link:

```sh
./scripts/attach_cad_part.sh cad/assembly/LeKiwi.FCStd drive_motor_mount-v11-2 CadDriveMotorMountV11_2 1240 0
./scripts/export_robot.sh
```

Here `1240` is only an example density in kg/m³. Use a measured printed mass instead of `0` for FDM or assembled parts; it accounts for infill, walls, and hardware. The exporter combines all solid CAD parts in a link with the parallel-axis theorem. Purchased components should use measured or vendor mass overrides.

Chassis joint metadata remains editable in the `LeKiwiJoints` group. SO-101 joint names, parents, children, axes, origins, and limits come from the pinned upstream URDF; together they form the deterministic composite Xacro contract.

### Measured chassis rod placements

The six screws identified by the operator in the marked underside photograph
are existing 20 mm-grid holes at `(±100, 0)` and `(±60, ±80)` mm. The working
`assembly/LeKiwi.FCStd` places all six existing rods there, with no central rod.
The visible rod placements and their ROS joint poses are both corrected. The
upper plate remains at `(0, 0, 50)` mm; its joint offset compensates for moving
the rod that is its parent. The original `LeKiwi_reference.FCStd` stays unchanged.

Run `./scripts/run_freecad_script.sh scripts/correct_chassis_rods.py` to verify
all six placements against holes in both editable plates. Add `--apply` to
reapply this measured layout. This does not resize the motor stands. Regenerate
RobotSkin exports after chassis corrections; old generated skins are not current.

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
