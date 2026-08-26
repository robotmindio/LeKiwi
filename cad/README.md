# Open CAD migration

`assembly/LeKiwi_reference.FCStd` is the complete Fusion STEP export imported into FreeCAD. It is the exact visual reference, but STEP cannot preserve Fusion sketches or its feature timeline.

`assembly/LeKiwi.FCStd` is the open CAD-to-ROS source. It contains the reference geometry plus 45 named links and 44 named joints copied from the validated URDF. Its current inertias and meshes are the known-good fallback values. This preserves the robot while it is reauthored part by part.

## Deterministic build

After changing `LeKiwi.FCStd`, run:

```sh
./scripts/export_robot.sh
python3 scripts/verify_xacro.py URDF/LeKiwi.urdf URDF/LeKiwi.urdf.xacro
```

`export_robot.sh` exports every reauthored CAD solid to `URDF/meshes/reauthored/` and then writes the complete Xacro. There is no hand-edited Xacro step. Unreauthored links retain their existing mesh and inertial values.

## Reauthoring a link

Model each replacement solid in the link's URDF coordinate frame, in millimetres, in `LeKiwi.FCStd` (or copy it into that document from `parts/`). Do not use the full-assembly placement: the exporter treats the solid's coordinates as link-local.

Attach the new solid and set its mass source:

```sh
./scripts/attach_cad_part.sh cad/assembly/LeKiwi.FCStd base_plate_layer1-v5 BasePlateReauthored 1240 0.385
./scripts/export_robot.sh
```

The arguments are FreeCAD document, URDF link, FreeCAD object name or unique label, material density in kg/m³, and mass override in kg. Use `0` for the override only for a uniform solid with a trustworthy density. For FDM parts, use the measured printed mass; this accounts for infill, walls, and hardware better than nominal plastic density. Run the command once for every solid belonging to a link.

For a link with attached CAD solids, the exporter calculates mass, centre of mass, and the full inertia tensor from the FreeCAD solids, rotates/translates nothing outside the link frame, and combines multiple solids with the parallel-axis theorem. Purchased components should use their measured or vendor mass as the override; their geometry still provides the centre and inertia distribution.

The joint names, parents, children, axes, origins, and limits are editable properties in the `LeKiwiJoints` group. This is the contract that makes the Xacro regeneration deterministic.

Regenerate the reference assembly only after replacing `reference/fusion/LeKiwi.stp`:

```sh
./scripts/import_step_reference.sh
./scripts/seed_robot_metadata.sh
```
