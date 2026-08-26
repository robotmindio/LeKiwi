# Open CAD migration

`assembly/LeKiwi_reference.FCStd` is the complete Fusion STEP export imported into FreeCAD. It is the exact visual reference, but STEP cannot preserve Fusion sketches or its feature timeline.

`assembly/LeKiwi.FCStd` is the open CAD-to-ROS source. It contains the reference geometry plus 45 named links and 44 named joints copied from the validated URDF. Every link has a link-local source object that drives the generated Xacro mesh:

- 2 editable FreeCAD laser-cut extrusions;
- 30 STEP BREP references; and
- 13 canonical URDF mesh references where the STEP and URDF exports differ by more than 2%.

The exact source and validation result for every link is recorded in [reference_mapping.json](reference_mapping.json). BREP references are editable in FreeCAD's Part workbench, and mesh references are editable meshes. Neither reconstructs Fusion's lost sketches or timeline.

The ordered set of native components still to rebuild is in [parts/](parts/README.md).

## Deterministic build

After changing `LeKiwi.FCStd`, run:

```sh
./scripts/export_robot.sh
python3 scripts/verify_xacro.py URDF/LeKiwi.urdf URDF/LeKiwi.urdf.xacro
./scripts/verify_cad_migration.sh
```

`export_robot.sh` exports all 45 link sources to `URDF/meshes/reauthored/` and then writes the complete Xacro. There is no hand-edited Xacro step. `verify_cad_migration.sh` checks this baseline migration against the original URDF; it is expected to fail after an intentional geometric redesign.

## Reauthoring a link

Model each replacement solid in the link's URDF coordinate frame, in millimetres, in `LeKiwi.FCStd` (or copy it into that document from `parts/`). Do not use the full-assembly placement: the exporter treats the solid's coordinates as link-local and emits reauthored visual/collision meshes with a zero origin. Attaching a new solid replaces that link's generated BREP/mesh reference, so subsequent Xacro output is deterministic from the new model.

Attach the new solid and set its mass source:

```sh
./scripts/attach_cad_part.sh cad/assembly/LeKiwi.FCStd base_plate_layer1-v5 BasePlateReauthored 1240 0.385
./scripts/export_robot.sh
```

The arguments are FreeCAD document, URDF link, FreeCAD object name or unique label, material density in kg/m³, and mass override in kg. Use `0` for the override only for a uniform solid with a trustworthy density. For FDM parts, use the measured printed mass; this accounts for infill, walls, and hardware better than nominal plastic density. Run the command once for every solid belonging to a link.

For a link with attached CAD solids, the exporter calculates mass, centre of mass, and the full inertia tensor from the FreeCAD solids, rotates/translates nothing outside the link frame, and combines multiple solids with the parallel-axis theorem. Purchased components should use their measured or vendor mass as the override; their geometry still provides the centre and inertia distribution.

The joint names, parents, children, axes, origins, and limits are editable properties in the `LeKiwiJoints` group. This is the contract that makes the Xacro regeneration deterministic. Reference objects intentionally keep the validated fallback inertias; activate CAD mass only after a native solid has a real material density or measured mass.

Regenerate the reference assembly only after replacing `reference/fusion/LeKiwi.stp`:

```sh
./scripts/import_step_reference.sh
./scripts/seed_robot_metadata.sh
./scripts/link_base_plate_sources.sh
./scripts/migrate_reference_links.sh --apply
./scripts/export_robot.sh
```
