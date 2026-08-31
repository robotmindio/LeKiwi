// Clean cylindrical SO-101 concept. This folder is intentionally disconnected
// from the production export pipeline while interfaces are tested.
include <generated/kinematics.scad>

part = "assembly"; // [assembly,arm,base_lower,base_upper,base_profile_lower,base_profile_upper,base_ribs_lower,base_ribs_upper,base_only,shoulder,upper_arm,lower_arm,wrist,gripper,moving_jaw,joint_cover_a,joint_cover_b,clearance_coupon,horn_coupon]
pose = "working"; // [home,working,lower_limits,upper_limits]
show_motors = true;
quality = 64;
$fn = quality;

// Printing and fit parameters. Tune clearance with clearance_coupon before
// committing to a complete print.
wall = 2.4;
fit_clearance = 0.6;
tube_od = 32;
hub_od = 42;
hub_width = 12;
horn_od = 24;
horn_pitch = 9.9;
horn_recess = 1.6;
horn_center = 6.4;
joint_od = 70;
joint_width = 31;
joint_gap = 1.2;
motor_size = [47, 42, 26];
cable_slot = [18, 18, 40];
m3_clearance = 3.3;
insert_od = 4.6;
boss_od = 8;

// The 7 mm maximum section matches the current plates. A 3 mm skin plus ribs
// carries bending load with less material than a solid plate.
base_skin = 3;
base_height = 7;
base_mount_pad = 8;
base_rim = 6;
base_rib = 8;

link_color = [0.82, 0.86, 0.88];
cover_color = [0.12, 0.15, 0.18];
accent_color = [0.18, 0.55, 0.68];
motor_color = [0.08, 0.08, 0.09];
base_color = [0.18, 0.20, 0.22];

q_home = [0, 0, 0, 0, 0, 0];
q_working = [0, -35, 65, -30, 0, 35];
q = pose == "lower_limits" ? [for (range = joint_limits) range[0]] :
    pose == "upper_limits" ? [for (range = joint_limits) range[1]] :
    pose == "home" ? q_home : q_working;

assert(tube_od > 2 * wall, "tube wall consumes the cable cavity");
assert(joint_od - 2 * wall >= norm([motor_size[0] + fit_clearance, motor_size[1] + fit_clearance]),
    "joint cover does not clear the motor cross-section");

function mounts(layer) = layer == "lower" ? base_lower_mounts : base_upper_mounts;
function dxf(layer) = layer == "lower" ?
    "../../../laser-cut/generated/base_plate_lower.dxf" :
    "../../../laser-cut/generated/base_plate_upper.dxf";

module at_pose(xyz, rpy) {
    translate(xyz) rotate(rpy) children();
}

module at_joint(name, angle = 0) {
    at_pose(joint_position(name), joint_rotation(name)) rotate([0, 0, angle]) children();
}

module orient_z(vector) {
    length = norm(vector);
    axis = cross([0, 0, 1], vector);
    angle = acos(vector[2] / length);
    if (norm(axis) < 0.0001)
        rotate(vector[2] < 0 ? [180, 0, 0] : [0, 0, 0]) children();
    else
        rotate(a = angle, v = axis) children();
}

module hollow_tube(vector, od = tube_od) {
    length = norm(vector);
    orient_z(vector)
        difference() {
            union() {
                cylinder(d = od, h = length);
                // A short flared socket transfers tube load into the motor cradle.
                translate([0, 0, max(0, length - 8)])
                    cylinder(d = hub_od + 2, h = min(8, length / 3));
            }
            translate([0, 0, -0.1]) cylinder(d = od - 2 * wall, h = length + 0.2);
            // Continuous underside route; a clip-on strip can close it after wiring.
            translate([-5, -od / 2 - 0.1, -0.1]) cube([10, wall + 0.7, length + 0.2]);
        }
}

module solid_strut(start, end, od) {
    translate(start) orient_z(end - start) cylinder(d = od, h = norm(end - start));
}

module hub() {
    difference() {
        cylinder(d = hub_od, h = hub_width, center = true);
        cylinder(d = horn_center, h = hub_width + 0.2, center = true);
        for (x = [-horn_pitch / 2, horn_pitch / 2], y = [-horn_pitch / 2, horn_pitch / 2])
            translate([x, y, 0]) cylinder(d = m3_clearance, h = hub_width + 0.2, center = true);
        // The horn seats on +Z; the unrecessed rear face carries tube load.
        translate([0, 0, hub_width / 2 - horn_recess / 2 + 0.05])
            cylinder(d = horn_od + fit_clearance, h = horn_recess + 0.1, center = true);
    }
}

module motor_cradle() {
    outer = [motor_size[0] + 2 * wall, motor_size[1] + 2 * wall, joint_width - 2 * wall];
    color(link_color)
        difference() {
            cube(outer, center = true);
            cube(motor_size + [fit_clearance, fit_clearance, 1], center = true);
            translate([0, -outer[1] / 2, 0]) cube(cable_slot, center = true);
        }
}

module cover_fasteners() {
    for (y = [-joint_od / 2 - 1, joint_od / 2 + 1])
        translate([0, y, 0]) rotate([0, 90, 0]) cylinder(d = m3_clearance, h = boss_od + 2, center = true);
}

module joint_cover_core() {
    difference() {
        union() {
            difference() {
                cylinder(d = joint_od, h = joint_width, center = true);
                cylinder(d = joint_od - 2 * wall, h = joint_width - 2 * wall, center = true);
                cylinder(d = hub_od + 2 * joint_gap, h = joint_width + 0.2, center = true);
            }
            for (y = [-joint_od / 2 - 1, joint_od / 2 + 1])
                translate([0, y, 0]) rotate([0, 90, 0]) cylinder(d = boss_od, h = boss_od, center = true);
        }
        translate([0, -joint_od / 2, 0]) cube(cable_slot, center = true);
        cover_fasteners();
        // Four short ventilation slots remain inside the protected lower quadrant.
        for (z = [-8, 0, 8])
            translate([0, joint_od / 2, z]) cube([16, wall * 3, 3], center = true);
    }
}

module joint_cover_half(side = 1) {
    intersection() {
        joint_cover_core();
        translate([side * (joint_od / 2 + 0.15), 0, 0])
            cube([joint_od, joint_od + 2 * boss_od, joint_width + 2], center = true);
    }
}

module joint_cover() {
    color(cover_color) {
        joint_cover_half(-1);
        joint_cover_half(1);
    }
    if (show_motors)
        color(motor_color, 0.75) cube(motor_size, center = true);
}

module link_structure(child_joint, od = tube_od) {
    endpoint = joint_position(child_joint);
    color(link_color) {
        hub();
        hollow_tube(endpoint, od);
        at_pose(endpoint, joint_rotation(child_joint)) motor_cradle();
    }
}

module link_body(child_joint, od = tube_od) {
    endpoint = joint_position(child_joint);
    link_structure(child_joint, od);
    at_pose(endpoint, joint_rotation(child_joint)) joint_cover();
}

module jaw_finger(length = 72, od = 18) {
    color(accent_color)
        difference() {
            union() {
                cylinder(d = hub_od, h = hub_width, center = true);
                rotate([90, 0, 0]) translate([0, 0, 3]) cylinder(d = od, h = length);
            }
            cylinder(d = hub_od - 2 * wall, h = hub_width + 0.2, center = true);
        }
}

module moving_jaw() {
    jaw_finger(72, 16);
}

module fixed_gripper_structure() {
    anchor = [-7.9, -0.218, -23.4];
    link_structure("gripper", 28);
    // The canonical gripper frame is 98.127 mm down -Z from this link. The
    // fixed finger ends on that axis; the moving finger uses the real joint.
    color(link_color) solid_strut(joint_position("gripper"), anchor, 18);
    translate(anchor) rotate([90, 0, 0]) jaw_finger(76, 17);
}

module gripper_link() {
    fixed_gripper_structure();
    at_pose(joint_position("gripper"), joint_rotation("gripper")) joint_cover();
    at_joint("gripper", q[5]) moving_jaw();
}

module wrist_chain() {
    link_body("wrist_roll", 30);
    at_joint("wrist_roll", q[4]) gripper_link();
}

module lower_arm_chain() {
    link_body("wrist_flex");
    at_joint("wrist_flex", q[3]) wrist_chain();
}

module upper_arm_chain() {
    link_body("elbow_flex");
    at_joint("elbow_flex", q[2]) lower_arm_chain();
}

module shoulder_chain() {
    link_body("shoulder_lift");
    at_joint("shoulder_lift", q[1]) upper_arm_chain();
}

module arm() {
    link_body("shoulder_pan", 38);
    at_joint("shoulder_pan", q[0]) shoulder_chain();
}

module compact_outline(layer) {
    // Convex load path through every functional mount. Generic unused grid
    // holes outside this envelope are intentionally omitted.
    hull()
        for (point = concat(base_lower_mounts, base_upper_mounts))
            translate(point) circle(r = base_mount_pad);
}

module legacy_plate(layer) {
    import(dxf(layer));
}

module base_profile(layer) {
    intersection() {
        legacy_plate(layer);
        compact_outline(layer);
    }
}

module base_rib_network(layer) {
    union() {
        difference() {
            compact_outline(layer);
            offset(delta = -base_rim) compact_outline(layer);
        }
        circle(r = 34);
        for (point = mounts(layer)) {
            hull() {
                circle(r = base_rib / 2);
                translate(point) circle(r = base_rib / 2);
            }
            translate(point) circle(r = base_mount_pad);
        }
    }
}

module base_ribs(layer) {
    intersection() {
        base_profile(layer);
        base_rib_network(layer);
    }
}

module ribbed_base(layer) {
    color(base_color)
        union() {
            linear_extrude(height = base_skin) base_profile(layer);
            linear_extrude(height = base_height) base_ribs(layer);
        }
}

module base_pair() {
    ribbed_base("lower");
    translate([0, 0, 50]) rotate([180, 0, 0]) ribbed_base("upper");
}

module assembly() {
    base_pair();
    translate([0, 0, 50]) at_pose(arm_mount_xyz, arm_mount_rpy) arm();
}

module clearance_coupon() {
    // Print once per material/profile. The three slots bracket fit_clearance.
    difference() {
        cube([72, 28, 6], center = true);
        for (index = [-1, 0, 1])
            translate([index * 22, 0, 0])
                cube([12 + fit_clearance + index * 0.2, 12 + fit_clearance + index * 0.2, 8], center = true);
    }
}

module horn_coupon() {
    difference() {
        cylinder(d = 32, h = 4);
        translate([0, 0, 4 - horn_recess])
            cylinder(d = horn_od + fit_clearance, h = horn_recess + 0.1);
        cylinder(d = horn_center, h = 4.2);
        for (x = [-horn_pitch / 2, horn_pitch / 2], y = [-horn_pitch / 2, horn_pitch / 2])
            translate([x, y, -0.1]) cylinder(d = m3_clearance, h = 4.2);
    }
}

if (part == "assembly") assembly();
else if (part == "arm") arm();
else if (part == "base_only") base_pair();
else if (part == "base_lower") ribbed_base("lower");
else if (part == "base_upper") ribbed_base("upper");
else if (part == "base_profile_lower") base_profile("lower");
else if (part == "base_profile_upper") base_profile("upper");
else if (part == "base_ribs_lower") base_ribs("lower");
else if (part == "base_ribs_upper") base_ribs("upper");
else if (part == "shoulder") link_structure("shoulder_lift");
else if (part == "upper_arm") link_structure("elbow_flex");
else if (part == "lower_arm") link_structure("wrist_flex");
else if (part == "wrist") link_structure("wrist_roll", 30);
else if (part == "gripper") fixed_gripper_structure();
else if (part == "moving_jaw") moving_jaw();
else if (part == "joint_cover_a") joint_cover_half(-1);
else if (part == "joint_cover_b") joint_cover_half(1);
else if (part == "clearance_coupon") clearance_coupon();
else if (part == "horn_coupon") horn_coupon();
else assert(false, str("unknown part: ", part));
