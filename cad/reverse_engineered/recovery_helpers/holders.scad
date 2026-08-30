// Reverse-engineered, print-ready holders from the legacy STL envelopes.
// Build one part with: openscad -D 'part="battery_mount_eu"' holders.scad

part = "battery_mount_eu";
$fn = 48;
eps = 0.05;

module m3_holes(points, r = 1.7, h = 30) {
    for (point = points)
        translate([point[0], point[1], -eps]) cylinder(r = r, h = h);
}

// A round mounting lug joined to the neighbouring rail.  Keeping this 2D
// lets the power-bank and USB holders share exactly the same construction.
module tab_2d(point, rail_x, side, r = 3.7) {
    translate(point) circle(r = r);
    if (side == "left")
        translate([point[0], point[1] - r]) square([rail_x - point[0], 2 * r]);
    else
        translate([rail_x, point[1] - r]) square([point[0] - rail_x, 2 * r]);
}

module outline_2d(origin, size, tabs = [], side = "left", r = 3.7) {
    union() {
        translate(origin) square(size);
        for (point = tabs) tab_2d(point, side == "left" ? origin[0] : origin[0] + size[0], side, r);
    }
}

module through_frame(origin, outer, opening_origin, opening, h, tabs = [], side = "left", tab_r = 3.7, hole_r = 1.7) {
    difference() {
        linear_extrude(height = h) outline_2d(origin, outer, tabs, side, tab_r);
        translate([opening_origin[0], opening_origin[1], -eps]) cube([opening[0], opening[1], h + 2 * eps]);
        m3_holes(tabs, hole_r, h + 2 * eps);
    }
}

module inverted_tray(origin, outer, opening_origin, opening, roof) {
    difference() {
        translate(origin) cube(outer);
        translate([opening_origin[0], opening_origin[1], -eps])
            cube([opening[0], opening[1], outer[2] - roof + eps]);
    }
}

// Extrude an X/Z section across Y, which is how the wired cable clip is made.
module extrude_y(depth) {
    translate([0, depth, 0]) rotate([90, 0, 0]) linear_extrude(height = depth) children();
}

module battery_mount_eu() {
    difference() {
        union() {
            // The original is a 6.5 mm plate below a 10 mm open U-wall.
            translate([-32, -39.5, -3.5]) cube([64, 79, 6.5]);
            translate([0, 0, 3])
                through_frame([-32, -39.5], [64, 79], [-29, -36.5], [58, 76], 10, [], "left", 0, 0);
        }
        // The legacy print deliberately has asymmetric lower M3 bores.
        translate([0, -10, -3.5 - eps]) cylinder(r = 1.5, h = 3 + 2 * eps, $fn = 24);
        translate([0, 10, -3.5 - eps]) cylinder(r = 1.75, h = 3 + 2 * eps, $fn = 24);
        // Both bores open into 5.6 mm-flat hex-nut pockets at z = -0.5 mm.
        for (y = [-10, 10])
            translate([0, y, -0.5 - eps]) rotate([0, 0, 30])
                cylinder(r = 3.2331615, h = 3.5 + 2 * eps, $fn = 6);
    }
}

module power_bank_holder_5v() {
    // 52.5 x 153 mm clearance, two M3 lugs 100 mm apart.
    through_frame([-4, -4], [60.5, 161], [0, 0], [52.5, 153], 7,
                  [[-7.5, 26.5], [-7.5, 126.5]]);
}

module cable_holder() {
    // This is the original clip's X/Z section, extracted from its planar side
    // face.  Keeping a contour rather than a triangle mesh leaves the part
    // editable while retaining its non-circular cable channel.
    profile = [
        [31.970402, 0.941858], [32, 0], [23.5, 0], [23.5, 1.5],
        [23.471178, 1.792635], [23.385818, 2.074025], [23.247204, 2.333355],
        [23.060659, 2.560660], [22.833355, 2.747204], [22.574024, 2.885819],
        [22.292635, 2.971178], [22, 3], [21.707365, 2.971178],
        [21.425976, 2.885819], [21.166645, 2.747204], [20.939341, 2.560660],
        [20.752796, 2.333355], [20.614182, 2.074025], [20.528822, 1.792635],
        [20.5, 1.5], [20.5, 0], [14, 0], [14, 4], [13.968459, 4.501333],
        [13.874332, 4.994760], [13.719106, 5.472498], [13.505227, 5.927015],
        [13.236068, 6.351141], [12.915874, 6.738188], [12.549696, 7.082053],
        [12.143307, 7.377312], [11.703117, 7.619308], [11.236068, 7.804226],
        [10.749525, 7.929149], [10.251163, 7.992107], [9.748837, 7.992107],
        [9.250475, 7.929149], [8.763932, 7.804226], [8.296883, 7.619308],
        [7.856693, 7.377312], [7.450304, 7.082053], [7.084126, 6.738188],
        [6.763932, 6.351141], [6.494773, 5.927015], [6.280894, 5.472498],
        [6.125668, 4.994760], [6.031541, 4.501333], [6, 4], [6, 0], [0, 0],
        [0.029599, 0.941858], [0.118279, 1.879998], [0.265691, 2.810720],
        [0.471253, 3.730348], [0.734152, 4.635255], [1.053353, 5.521868],
        [1.427594, 6.386689], [1.855400, 7.226305], [2.335081, 8.037402],
        [2.864745, 8.816779], [3.442301, 9.561359], [4.065471, 10.268207],
        [4.731793, 10.934529], [5.438640, 11.557698], [6.183221, 12.135255],
        [6.962598, 12.664919], [7.773695, 13.144600], [8.613311, 13.572406],
        [9.478131, 13.946648], [10.364745, 14.265848], [11.269651, 14.528748],
        [12.189281, 14.734309], [13.120002, 14.881721], [14.058143, 14.970401],
        [15, 15], [17, 15], [17.941858, 14.970401], [18.879999, 14.881721],
        [19.810720, 14.734309], [20.730349, 14.528748], [21.635256, 14.265848],
        [22.521868, 13.946648], [23.386690, 13.572406], [24.226305, 13.144600],
        [25.037401, 12.664919], [25.816778, 12.135255], [26.561359, 11.557698],
        [27.268206, 10.934529], [27.934530, 10.268207], [28.557699, 9.561359],
        [29.135256, 8.816779], [29.664919, 8.037402], [30.144600, 7.226305],
        [30.572405, 6.386689], [30.946648, 5.521868], [31.265848, 4.635255],
        [31.528748, 3.730348], [31.734308, 2.810720], [31.881720, 1.879998]
    ];
    difference() {
        union() {
            extrude_y(7.5) polygon(points = profile);
            linear_extrude(height = 4)
                union() {
                    translate([0, 0]) square([6, 7.5]);
                    tab_2d([-4, 3.75], 0, "left", 3.6);
                    translate([23.5, 0]) square([8.5, 7.5]);
                    tab_2d([36, 3.75], 32, "right", 3.6);
                }
        }
        m3_holes([[-4, 3.75], [36, 3.75]], 1.6, 4 + 2 * eps);
    }
}

module usb_connector_case() {
    tabs = [[-6, 31], [34, 31], [-6, 111], [34, 111]];
    port = [
        [11.5, 0], [11.5, 3.550510], [11.019399, 4.165329],
        [10.686972, 4.871354], [10.519243, 5.633486], [10.524552, 6.413839],
        [10.702635, 7.173619], [11.044638, 7.875055], [11.533559, 8.483278],
        [12.145094, 8.968050], [12.848841, 9.305273], [13.609815, 9.478183],
        [14.390185, 9.478183], [15.151159, 9.305273], [15.854906, 8.968050],
        [16.466440, 8.483278], [16.955362, 7.875055], [17.297365, 7.173619],
        [17.475449, 6.413839], [17.480757, 5.633486], [17.313028, 4.871354],
        [16.980600, 4.165329], [16.5, 3.550510], [16.5, 0]
    ];
    difference() {
        union() {
            // The v1 shell opens downward: 4 mm side rails, a 4 mm roof,
            // and 4 mm closed end caps around a 28 x 122 mm connector bay.
            inverted_tray([-4, -4, 0], [36, 130, 16], [0, 0], [28, 122], 4);
            linear_extrude(height = 4)
                union() {
                    for (tab = [[-6, 31], [-6, 111]]) tab_2d(tab, -4, "left", 3.7);
                    for (tab = [[34, 31], [34, 111]]) tab_2d(tab, 32, "right", 3.7);
                }
            // The central length is an L-channel, not a full U-channel.
            translate([28, 35, 12]) cube([4, 72, 4]);
        }
        m3_holes(tabs, 1.7, 4 + 2 * eps);
        translate([28, 35, -eps]) cube([4, 72, 12 + eps]);
        // The front end cap has a 5 mm lead-in that opens into the USB bulb.
        translate([0, -4 - eps, 0]) extrude_y(4 + 2 * eps) polygon(points = port);
        // Mount lugs are relieved above their 4 mm plate so they do not trap
        // the cable case walls.
        for (tab = tabs)
            translate([tab[0], tab[1], 4 - eps]) cylinder(r = 3, h = 12 + 2 * eps);
    }
}

if (part == "battery_mount_eu")
    battery_mount_eu();
else if (part == "5v_power_bank_holder")
    power_bank_holder_5v();
else if (part == "cable_holder_v0")
    cable_holder();
else if (part == "usb_connector_case_v1")
    usb_connector_case();
else
    assert(false, str("Unknown part: ", part));
