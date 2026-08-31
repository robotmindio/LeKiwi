$fn = 48;
part = "mount"; // [mount,fit_test]

// Placement: camera faces +Y and pitches down toward +Y.
target_optical_height = 300.0;
deck_height_above_floor = 90.0;
camera_axis_above_underside = 24.0;
pitch = 8.0;

// Base-removed Astra Pro interface, measured from the physical camera.
boss_length = 26.0;
boss_depth = 7.9;
boss_projection = 4.5;
boss_clearance = 0.3; // ponytail: tune only this if the printed pocket is tight.
m2_spacing = 18.0;
m2_clearance = 2.4;
interface_skin = 2.4;

// Physical between-wheel mounting pair.
m3_spacing = 44.0;
m3_clearance = 3.6;
m3_head_clearance = 6.5;
base_width = 54.0;
base_depth = 30.0;
base_thickness = 5.0;

saddle_width = 40.0;
saddle_depth = 20.0;
saddle_thickness = boss_projection + boss_clearance + interface_skin;
saddle_contact_z = target_optical_height
    - deck_height_above_floor
    - camera_axis_above_underside * cos(pitch);

leg_width = 6.0;
leg_depth = 10.0;
leg_centres = [-15.5, 0, 15.5];
leg_taper_height = 55.0;
leg_top_z = saddle_contact_z - saddle_thickness * cos(pitch) + 1.0;

assert(m3_spacing == 44.0);
assert(saddle_thickness - boss_projection - boss_clearance >= 2.0);
assert(saddle_width > boss_length + 2 * boss_clearance);
assert(saddle_depth > boss_depth + 2 * boss_clearance);

module saddle() {
    difference() {
        translate([-saddle_width / 2, -saddle_depth / 2, -saddle_thickness])
            cube([saddle_width, saddle_depth, saddle_thickness]);

        // The surrounding top face seats on the camera; the boss drops into this pocket.
        translate([
            -(boss_length + 2 * boss_clearance) / 2,
            -(boss_depth + 2 * boss_clearance) / 2,
            -(boss_projection + boss_clearance)
        ])
            cube([
                boss_length + 2 * boss_clearance,
                boss_depth + 2 * boss_clearance,
                boss_projection + boss_clearance + 0.1
            ]);

        for (x = [-m2_spacing / 2, m2_spacing / 2])
            translate([x, 0, -saddle_thickness - 0.1])
                cylinder(h=saddle_thickness + 0.3, d=m2_clearance);
    }
}

module mount() {
    difference() {
        union() {
            translate([-base_width / 2, -base_depth / 2, 0])
                cube([base_width, base_depth, base_thickness]);

            for (x = leg_centres) {
                hull() {
                    translate([x - leg_width / 2, -base_depth / 2, base_thickness])
                        cube([leg_width, base_depth, 1]);
                    translate([x - leg_width / 2, -leg_depth / 2, leg_taper_height])
                        cube([leg_width, leg_depth, 1]);
                }
                translate([x - leg_width / 2, -leg_depth / 2, leg_taper_height])
                    cube([leg_width, leg_depth, leg_top_z - leg_taper_height]);
            }

            translate([0, 0, saddle_contact_z])
                rotate([-pitch, 0, 0])
                    saddle();
        }

        for (x = [-m3_spacing / 2, m3_spacing / 2]) {
            translate([x, 0, -0.1])
                cylinder(h=base_thickness + 0.2, d=m3_clearance);
            translate([x, 0, base_thickness - 2.2])
                cylinder(h=2.3, d=m3_head_clearance);
        }
    }
}

if (part == "mount")
    mount();
else if (part == "fit_test")
    translate([0, 0, saddle_thickness]) saddle();
else
    assert(false, "part must be mount or fit_test");
