# Open CAD migration

`assembly/LeKiwi_reference.FCStd` is the complete Fusion STEP export imported into FreeCAD. It preserves the full assembly's exact geometry and named components, but is a reference model: STEP cannot preserve Fusion sketches or its feature timeline.

Use the reference assembly to rebuild only a part when it needs changing. Put each new parametric `.FCStd` source in `parts/`, then replace the matching reference component in the FreeCAD assembly.

Regenerate the reference assembly after replacing `reference/fusion/LeKiwi.stp`:

```sh
./scripts/import_step_reference.sh
```

The ROS source is [URDF/LeKiwi.urdf.xacro](../URDF/LeKiwi.urdf.xacro). Its `mesh_dir` property defaults to the current mesh directory, so it preserves the existing URDF mesh layout while allowing a ROS package path to be substituted later.
