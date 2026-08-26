// Laser profiles of the original 3D-printed base plates.
// Select one plate, then export as DXF with OpenSCAD.
plate = "lower"; // [lower,upper]

projection(cut = true)
    import(plate == "lower"
        ? "../3DPrintMeshes/base_plate_layer1.stl"
        : "../3DPrintMeshes/base_plate_layer2.stl");
