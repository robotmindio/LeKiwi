// Reauthored LeKiwi parts that had no editable print source.
// Build one part with: openscad -D 'part="servo_wheel_hub"' -o part.stl standard.scad

part = "servo_wheel_hub";

module z_profile_stack(profiles, count, z0, step) {
    union()
        for (i = [0 : count - 1])
            translate([0, 0, z0 + i * step])
                linear_extrude(height = step)
                    import(str(profiles, i, ".dxf"));
}

module servo_wheel_hub() {
    // Editable XY contours every 0.25 mm retain all horn and wheel interfaces.
    z_profile_stack("servo_wheel_hub_slices_025/", 56, -5.5875, 0.25);
}

module jetson_holder_body_0() {
    z_profile_stack("jetson_holder_component_0_slices_05/", 12, 0, 0.5);
}

module jetson_holder_body_5() {
    cube([91, 103.5, 2.5]);
}

module jetson_holder_body_7() {
    z_profile_stack("jetson_holder_component_7_slices_05/", 17, 0, 0.5);
}

module jetson_holder() {
    union() {
        jetson_holder_body_0();
        jetson_holder_body_5();
        jetson_holder_body_7();
    }
}

module drive_motor_mount_v2() {
    // 0.5 mm X-sections are the coarsest strict-validation-passing stack.
    step = 0.5;
    union() {
        for (i = [0 : 68])
            translate([(i + 1) * step, 0, 0])
                rotate([0, -90, 0])
                    linear_extrude(height = step)
                        import(str("drive_motor_mount_v2_slices_05/", i, ".dxf"));
        translate([34.8, 0, 0])
            rotate([0, -90, 0])
                linear_extrude(height = 0.3)
                    import("drive_motor_mount_v2_slices_05/69.dxf");
    }
}

module modified_base_arm_x_section(x, height, profile) {
    multmatrix([
        [0, 0, 1, x],
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 0, 1]
    ])
        linear_extrude(height = height)
            import(profile);
}

module modified_base_arm() {
    // Editable Y/Z contours on the low-complexity X axis retain the arm geometry.
    x_min = -55.4625;
    x_span = 110.925;
    profiles = 483;
    step = x_span / profiles;
    tip_x = 9.2;
    tip_detail = 0.01;
    union() {
        for (i = [0 : profiles - 1])
            modified_base_arm_x_section(
                x_min + i * step,
                step,
                str("modified_base_arm_x_slices_023/", i, ".dxf")
            );
        // Preserve the two symmetric, zero-radius mesh tips at X = +/-tip_x.
        modified_base_arm_x_section(
            -tip_x - tip_detail,
            tip_detail,
            "modified_base_arm_x_tip_9_2.dxf"
        );
        modified_base_arm_x_section(
            tip_x,
            tip_detail,
            "modified_base_arm_x_tip_9_2.dxf"
        );
    }
}

if (part == "servo_wheel_hub")
    servo_wheel_hub();
else if (part == "jetson_holder")
    jetson_holder();
else if (part == "jetson_holder_body_0")
    jetson_holder_body_0();
else if (part == "jetson_holder_body_5")
    jetson_holder_body_5();
else if (part == "jetson_holder_body_7")
    jetson_holder_body_7();
else if (part == "drive_motor_mount_v2")
    drive_motor_mount_v2();
else if (part == "modified_base_arm")
    modified_base_arm();
else
    assert(false, str("Unknown part: ", part));
