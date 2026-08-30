// Editable contour-stack reconstructions for Dynamixel-specific LeKiwi prints.
// Build one part with:
// openscad -D 'part="dynamixel_modified_base_arm"' -o part.stl dynamixel.scad

part = "dynamixel_modified_base_arm";

module z_stack(directory, starts, heights) {
    assert(len(starts) == len(heights));
    union()
        for (i = [0 : len(starts) - 1])
            translate([0, 0, starts[i]])
                linear_extrude(height = heights[i])
                    import(str(directory, "/", i, ".dxf"));
}

module uniform_z_stack(directory, start, height, count) {
    z_stack(directory,
        [for (i = [0 : count - 1]) start + i * height],
        [for (i = [0 : count - 1]) height]);
}

module dynamixel_modified_base_arm() {
    // Coarsest recovered stack that clears the 0.25 mm / 0.10 mm surface gate.
    z_stack("contours/dynamixel_modified_base_arm",
        [-104.469284, -103.969284, -103.469284, -102.969284,
         -102.469284, -101.969284, -101.469284, -100.869284,
         -100.269284, -99.6692841, -99.0692841, -98.4692841,
         -97.8692841, -97.2692841, -96.6692841, -96.0692841],
        [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6,
         0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6]);
}

module dynamixel_drive_motor_mount() {
    // 230 sections, 0.239565 mm each: the coarsest tested strict-pass stack.
    uniform_z_stack("contours/dynamixel_drive_motor_mount",
        -27.5499992371, 55.0999984741 / 230, 230);
}

if (part == "dynamixel_modified_base_arm")
    dynamixel_modified_base_arm();
else if (part == "dynamixel_drive_motor_mount")
    dynamixel_drive_motor_mount();
else
    assert(false, str("Unknown Dynamixel part: ", part));
