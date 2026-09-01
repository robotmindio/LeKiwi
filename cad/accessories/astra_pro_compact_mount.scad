$fn = 48;

// Camera faces +Y; positive pitch tilts its view downward toward +Y.
pitch = 8.0;
camera_contact_height = 15.5;

// Base-removed Astra Pro interface measured from the physical camera.
boss_length = 26.0;
boss_depth = 7.9;
boss_projection = 6.0;
boss_clearance = 0.3; // ponytail: increase only if the printed pocket is tight.
m2_spacing = 18.0;
m2_clearance = 2.4;
m2_head_diameter = 4.5;
m2_head_access = m2_head_diameter + 0.2;
interface_skin = 2.4;

// Physical mounting pair in the clear space between two wheels.
m3_spacing = 44.0;
m3_clearance = 3.6;
m3_head_clearance = 6.5;
base_width = 54.0;
base_depth = 30.0;
base_thickness = 5.0;

saddle_width = 37.0;
saddle_depth = 20.0;
saddle_thickness = boss_projection + boss_clearance + interface_skin;
saddle_half_y = saddle_depth / 2 * cos(pitch);
saddle_height_delta = saddle_depth / 2 * sin(pitch);

assert(m3_spacing == 44.0);
assert(m2_head_access > m2_head_diameter);
assert(saddle_thickness - boss_projection - boss_clearance >= 2.0);
assert(camera_contact_height - saddle_height_delta - base_thickness >= saddle_thickness);

module saddle_frame() {
    translate([0, 0, camera_contact_height])
        rotate([-pitch, 0, 0])
            children();
}

module support_wedge() {
    polyhedron(
        points=[
            [-saddle_width / 2, -saddle_half_y, base_thickness],
            [ saddle_width / 2, -saddle_half_y, base_thickness],
            [ saddle_width / 2,  saddle_half_y, base_thickness],
            [-saddle_width / 2,  saddle_half_y, base_thickness],
            [-saddle_width / 2, -saddle_half_y, camera_contact_height + saddle_height_delta],
            [ saddle_width / 2, -saddle_half_y, camera_contact_height + saddle_height_delta],
            [ saddle_width / 2,  saddle_half_y, camera_contact_height - saddle_height_delta],
            [-saddle_width / 2,  saddle_half_y, camera_contact_height - saddle_height_delta]
        ],
        faces=[
            [0, 3, 2, 1],
            [4, 5, 6, 7],
            [0, 1, 5, 4],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [3, 0, 4, 7]
        ]
    );
}

difference() {
    union() {
        translate([-base_width / 2, -base_depth / 2, 0])
            cube([base_width, base_depth, base_thickness]);
        support_wedge();
    }

    // Camera boss relief, open at the tilted top face.
    saddle_frame()
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

    // M2 screws enter from below; the larger bores stop at the saddle skin.
    for (x = [-m2_spacing / 2, m2_spacing / 2]) {
        saddle_frame()
            translate([x, 0, -30])
                cylinder(h=31, d=m2_clearance);
        saddle_frame()
            translate([x, 0, -30])
                cylinder(h=30 - saddle_thickness + 0.05, d=m2_head_access);
    }

    // Insert these M3 screws before attaching the camera, then add locknuts below.
    for (x = [-m3_spacing / 2, m3_spacing / 2]) {
        translate([x, 0, -0.1])
            cylinder(h=30, d=m3_clearance);
        translate([x, 0, base_thickness - 2.2])
            cylinder(h=30, d=m3_head_clearance);
    }
}
