$fn = 48;

// Camera interface measured from the base-removed Astra Pro.
boss_length = 26.0;
boss_height = 7.9;
boss_projection = 4.5;
boss_clearance = 0.3; // ponytail: tune for the printer if the first fit is tight.
m2_spacing = 18.0;
m2_clearance = 2.4;
interface_skin = 2.4;

// Reuses the two front holes occupied by LeKiwi's Camera-Mount-v8.
deck_hole_spacing = 40.0;
m3_clearance = 3.6;
m3_head_clearance = 6.5;
base_width = 50.0;
base_depth = 20.0;
base_thickness = 4.5;

camera_center_z = 25.0;
pad_width = 36.0;
pad_height = 16.0;
pad_depth = boss_projection + boss_clearance + interface_skin;
pad_front_y = base_depth / 2;
pad_back_y = pad_front_y - pad_depth;
pad_bottom_z = camera_center_z - pad_height / 2;
spine_width = 18.0;

module gusset(x) {
    hull() {
        translate([x, -base_depth / 2 + 1, base_thickness]) cube([4, 1, 1]);
        translate([x, pad_back_y, base_thickness]) cube([4, pad_depth, 1]);
        translate([x, pad_back_y, pad_bottom_z - 1]) cube([4, pad_depth, 1]);
    }
}

difference() {
    union() {
        translate([-base_width / 2, -base_depth / 2, 0])
            cube([base_width, base_depth, base_thickness]);
        translate([-spine_width / 2, pad_back_y, base_thickness])
            cube([spine_width, pad_depth, pad_bottom_z - base_thickness]);
        translate([-pad_width / 2, pad_back_y, pad_bottom_z])
            cube([pad_width, pad_depth, pad_height]);
        gusset(-spine_width / 2 - 5);
        gusset(spine_width / 2 + 1);
    }

    // M3 deck screws, counterbored flush on top.
    for (x = [-deck_hole_spacing / 2, deck_hole_spacing / 2]) {
        translate([x, 0, -0.1])
            cylinder(h=base_thickness + 0.2, d=m3_clearance);
        translate([x, 0, base_thickness - 2.2])
            cylinder(h=2.3, d=m3_head_clearance);
    }

    // Relief lets the outer pad seat on the housing without loading the boss.
    translate([
        -(boss_length + 2 * boss_clearance) / 2,
        pad_front_y - boss_projection - boss_clearance,
        camera_center_z - (boss_height + 2 * boss_clearance) / 2
    ])
        cube([
            boss_length + 2 * boss_clearance,
            boss_projection + boss_clearance + 0.1,
            boss_height + 2 * boss_clearance
        ]);

    for (x = [-m2_spacing / 2, m2_spacing / 2])
        translate([x, pad_front_y + 0.1, camera_center_z])
            rotate([90, 0, 0])
                cylinder(h=pad_depth + 0.2, d=m2_clearance);
}
