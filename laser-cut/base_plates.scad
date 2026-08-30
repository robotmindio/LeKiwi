// Editable laser profiles of the base plates used by the validated assembly.
// Select one plate, then export as DXF with OpenSCAD.
plate = "lower"; // [lower,upper]

import(plate == "lower"
    ? "generated/base_plate_lower.dxf"
    : "generated/base_plate_upper.dxf");
