// Editable recovery of 3DPrintMeshes/dynamixel_specific/lipo_battery_mount.stl.
// Render: openscad -o lipo_battery_mount.stl lipo_battery_mount.scad

base_z = -3.5;
transition_z = -0.5;
floor_z = 3;
top_z = 13;

module rectangle(x0, y0, x1, y1) {
    translate([x0, y0]) square([x1 - x0, y1 - y0]);
}

module lipo_battery_mount() {
    difference() {
        union() {
            translate([-31, -39.5, base_z]) cube([62, 79, floor_z - base_z]);
            translate([0, 0, floor_z])
                linear_extrude(top_z - floor_z)
                    difference() {
                        rectangle(-31, -39.5, 31, 39.5);
                        rectangle(-28, -36.5, 28, 39.5);
                    }
        }

        // Through holes are round below transition_z and hexagonal above it.
        for (center = [[0, -14], [0, 10]])
            translate([center[0], center[1], base_z])
                cylinder(h = transition_z - base_z, r = 1.75, $fn = 24);

        translate([0, 0, transition_z])
            linear_extrude(floor_z - transition_z) {
                polygon([
                    [0, -17.233161], [2.8, -15.616581], [2.8, -12.383419],
                    [0, -10.766839], [-2.8, -12.383419], [-2.8, -15.616581]
                ]);
                polygon([
                    [-2.827208, 11.568512], [-2.771975, 8.335822], [0.055232, 6.767310],
                    [2.827208, 8.431488], [2.771975, 11.664177], [-0.055232, 13.232689]
                ]);
            }
    }
}

lipo_battery_mount();
