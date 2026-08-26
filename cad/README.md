# Open CAD migration

`assembly/LeKiwi_reference.FCStd` is the complete Fusion STEP export imported into FreeCAD. It is the dimensional reference; STEP cannot retain Fusion sketches or its feature timeline.

`assembly/LeKiwi.FCStd` is the open CAD-to-ROS source. Its active `CadParts` cover all 45 URDF links:

- 2 editable FreeCAD laser-cut extrusions;
- 10 links driven by 6 native parametric FreeCAD printed-part sources;
- 23 STEP BREP references; and
- 10 canonical URDF mesh references where the STEP and URDF exports differ by more than 2%.

The exact source and validation result for every link is recorded in [reference_mapping.json](reference_mapping.json). The hidden `LeKiwiReferenceParts` group is retained only for placement and validation; it is not the geometry exported for a reauthored part.

## Native printed-part sources

The complete LeKiwi-specific manufactured set represented by the URDF is editable in [parts/](parts/README.md): the two laser-cut plates plus `drive_motor_mount.FCStd`, `omni_wheel_mount.FCStd`, `servo_controller_mount.FCStd`, `lipo_battery_mount.FCStd`, `base_camera_mount.FCStd`, and `wrist_camera_mount.FCStd`.

Each printed-part file has an `Editable dimensions` (`Parameters`) object and a normal FreeCAD feature tree ending in `Final`; it contains profile features, Part extrusions, primitives, fuses, and cuts—not an imported mesh or opaque BREP wrapper. Open a source file in FreeCAD, change a parameter or profile feature, and save it. Then relink and regenerate:

```sh
./scripts/link_native_part_sources.sh
./scripts/export_robot.sh
./scripts/verify_native_part_sources.sh
```

`build_native_part_sources.sh` reconstructs the six initial source files from the validated STEP/STL references. It intentionally overwrites those source files, so use it to reset or regenerate a baseline, not after manual edits you intend to keep.

Five models preserve their STEP component frame and are placed into the URDF link frame by `link_native_part_sources.sh`. The omni-wheel source uses the canonical URDF mesh frame because its Fusion STEP revision does not match the shipped URDF mesh; its editable profiles are derived once from canonical STL planes and then built as normal FreeCAD features. The linker's validation must remain below the 2% geometry tolerance before it saves the assembly.

## Deterministic build

After changing a source or robot metadata, run:

```sh
./scripts/export_robot.sh
python3 scripts/verify_xacro.py URDF/LeKiwi.urdf URDF/LeKiwi.urdf.xacro
./scripts/verify_cad_migration.sh
```

`export_robot.sh` exports all 45 link sources to `URDF/meshes/reauthored/` and writes the complete Xacro. There is no hand-edited Xacro step. `verify_cad_migration.sh` checks the baseline migration against the original URDF and is expected to fail after an intentional geometric redesign.

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
