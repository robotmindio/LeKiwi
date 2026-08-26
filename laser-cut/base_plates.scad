// Laser profiles of the base plates used by the validated URDF/Fusion assembly.
// Select one plate, then export as DXF with OpenSCAD.
plate = "lower"; // [lower,upper]

projection(cut = true)
    import(plate == "lower"
        ? "../URDF/meshes/base_plate_layer1-v5.stl"
        : "../URDF/meshes/base_plate_layer2-v3.stl");
