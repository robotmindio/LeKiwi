// Bottom-up SO-101 study. The arm is built from one repeated vocabulary:
// drive flange -> hollow round link -> serviceable servo pod.
include <generated/kinematics.scad>

part = "assembly"; // [assembly,arm,base_lower,base_upper,base_profile_lower,base_profile_upper,base_ribs_lower,base_ribs_upper,base_only,base_column,shoulder,upper_arm,lower_arm,wrist,gripper,moving_jaw,servo_lid,clearance_coupon,horn_coupon]
pose = "working"; // [home,working,lower_limits,upper_limits]
show_motors = true;
show_lids = true;
quality = 48;
$fn = quality;

// Shared mechanical geometry. The motor envelope and shaft location come from
// the canonical SO-101 STS3215 mesh; generate_kinematics.py verifies every
// servo shaft against its joint frame.
wall = 2.6;
fit_clearance = 0.6;
link_od = 30;
base_link_od = 36;
base_foot_od = 62;
base_foot_depth = 7;
base_foot_overlap = 2;
drive_od = 32;
drive_width = 7;
drive_offset = -8.5;
bezel_od = 30;
bezel_width = 5;
servo_body = [45.4, 24.8, 39.6];
servo_shaft = [12.5, 0, 18.7];
pod_outer = servo_body + [2 * wall + fit_clearance, 2 * wall + fit_clearance, 2 * wall + fit_clearance];
pod_radius = 5;
lid_depth = 4;
lid_boss_od = 8;
lid_insert_od = 4.6;
m3_clearance = 3.3;
horn_od = 24;
horn_radius = 7;
horn_recess = 1.6;
horn_center = 6.4;

// Base plates keep the current functional placements while their load paths
// are reduced to a perimeter, radial ribs and local pads.
base_skin = 3;
base_height = 7;
base_mount_pad = 8;
base_rim = 6;
base_rib = 8;

link_color = [0.78, 0.82, 0.84];
pod_color = [0.17, 0.19, 0.22];
lid_color = [0.10, 0.12, 0.14];
motor_color = [0.04, 0.05, 0.06];
accent_color = [0.12, 0.48, 0.62];
base_color = [0.15, 0.17, 0.19];

q_home = [0, 0, 0, 0, 0, 0];
q_working = [0, -35, 65, -30, 0, 35];
q = pose == "lower_limits" ? [for (range = joint_limits) range[0]] :
    pose == "upper_limits" ? [for (range = joint_limits) range[1]] :
    pose == "home" ? q_home : q_working;

assert(link_od > 2 * wall, "link wall consumes the cable conduit");
assert(pod_outer[1] > servo_body[1] + fit_clearance, "servo pod has no wall");

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

module at_servo(name) {
    at_pose(servo_position(name), servo_rotation(name)) children();
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

module rounded_prism(size, radius) {
    linear_extrude(height = size[2], center = true)
        hull()
            for (x = [-size[0] / 2 + radius, size[0] / 2 - radius],
                 y = [-size[1] / 2 + radius, size[1] / 2 - radius])
                translate([x, y]) circle(r = radius);
}

module hollow_link(vector, od = link_od) {
    length = norm(vector);
    orient_z(vector)
        difference() {
            cylinder(d = od, h = length);
            translate([0, 0, -0.1]) cylinder(d = od - 2 * wall, h = length + 0.2);
        }
}

module hollow_link_between(start, end, od = link_od) {
    translate(start) hollow_link(end - start, od);
}

module solid_link(start, end, od) {
    translate(start) orient_z(end - start) cylinder(d = od, h = norm(end - start));
}

module horn_pattern(height = 30) {
    cylinder(d = horn_center, h = height, center = true);
    for (angle = [0 : 90 : 270])
        rotate([0, 0, angle]) translate([horn_radius, 0, 0])
            cylinder(d = m3_clearance, h = height, center = true);
    translate([0, 0, drive_width / 2 - horn_recess / 2 + 0.05])
        cylinder(d = horn_od + fit_clearance, h = horn_recess + 0.1, center = true);
}

module drive_flange_blank() {
    cylinder(d = drive_od, h = drive_width, center = true);
}

module shaft_bezel() {
    difference() {
        cylinder(d = bezel_od, h = bezel_width, center = true);
        cylinder(d = horn_od + fit_clearance, h = bezel_width + 0.2, center = true);
    }
}

module pod_shell_local() {
    difference() {
        rounded_prism(pod_outer, pod_radius);
        rounded_prism(servo_body + [fit_clearance, fit_clearance, fit_clearance], 2.5);
        translate(servo_shaft)
            cylinder(d = horn_od + fit_clearance, h = wall * 4, center = true);
        // The cable exits through the removable rear cap.
        translate([-pod_outer[0] / 2, 0, -pod_outer[2] / 4])
            cube([wall * 3, 12, 10], center = true);
    }
}

module lid_bosses(x0, length, hole) {
    for (y = [-pod_outer[1] / 2, pod_outer[1] / 2])
        translate([x0, y, 0]) rotate([0, 90, 0])
            difference() {
                cylinder(d = lid_boss_od, h = length, center = true);
                cylinder(d = hole, h = length + 0.2, center = true);
            }
}

module servo_cradle_local() {
    split = -pod_outer[0] / 2 + lid_depth;
    receiver = 7;
    union() {
        intersection() {
            pod_shell_local();
            translate([(split + pod_outer[0] / 2) / 2, 0, 0])
                cube([pod_outer[0] / 2 - split, pod_outer[1] + 12, pod_outer[2] + 2], center = true);
        }
        lid_bosses(split + receiver / 2, receiver, lid_insert_od);
    }
}

module servo_lid_local() {
    difference() {
        union() {
            intersection() {
                pod_shell_local();
                translate([-pod_outer[0] / 2 + lid_depth / 2, 0, 0])
                    cube([lid_depth, pod_outer[1] + 12, pod_outer[2] + 2], center = true);
            }
            lid_bosses(-pod_outer[0] / 2 + lid_depth / 2, lid_depth, m3_clearance);
        }
        for (y = [-pod_outer[1] / 2, pod_outer[1] / 2])
            translate([-pod_outer[0] / 2 + lid_depth / 2, y, 0])
                rotate([0, 90, 0]) cylinder(d = m3_clearance, h = lid_depth + 0.2, center = true);
    }
}

module motor_local() {
    rounded_prism(servo_body, 3);
    translate(servo_shaft) cylinder(d = 20, h = 3.2, center = true);
}

module printed_link(child_joint, od = link_od) {
    endpoint = joint_position(child_joint);
    color(link_color)
        difference() {
            union() {
                translate([0, 0, drive_offset]) drive_flange_blank();
                hollow_link_between([0, 0, drive_offset], endpoint, od);
                at_joint(child_joint) shaft_bezel();
                color(pod_color) at_servo(child_joint) servo_cradle_local();
            }
            translate([0, 0, drive_offset]) horn_pattern();
        }
}

module fitted_link(child_joint, od = link_od) {
    printed_link(child_joint, od);
    if (show_lids)
        color(lid_color) at_servo(child_joint) servo_lid_local();
    if (show_motors)
        color(motor_color) at_servo(child_joint) motor_local();
}

module jaw_finger(length = 72, od = 16) {
    hull() {
        sphere(d = od);
        translate([0, -length, 0]) sphere(d = od * 0.72);
    }
}

module moving_jaw() {
    color(accent_color)
        difference() {
            translate([0, 0, drive_offset])
                union() {
                    cylinder(d = drive_od, h = drive_width, center = true);
                    jaw_finger();
                }
            translate([0, 0, drive_offset]) horn_pattern();
        }
}

module base_column_printed() {
    endpoint = joint_position("shoulder_pan");
    color(link_color)
        difference() {
            union() {
                translate([0, 0, -base_foot_depth])
                    cylinder(d = base_foot_od, h = base_foot_depth + base_foot_overlap);
                hollow_link(endpoint, base_link_od);
                at_joint("shoulder_pan") shaft_bezel();
                color(pod_color) at_servo("shoulder_pan") servo_cradle_local();
            }
            for (point = arm_base_mounts)
                translate([point[0], point[1], -base_foot_depth - 0.1])
                    cylinder(d = m3_clearance, h = base_foot_depth + base_foot_overlap + 0.2);
        }
}

module base_column() {
    base_column_printed();
    if (show_lids)
        color(lid_color) at_servo("shoulder_pan") servo_lid_local();
    if (show_motors)
        color(motor_color) at_servo("shoulder_pan") motor_local();
}

module gripper_printed() {
    frame = [-7.9, -0.218, -98.1274];
    union() {
        printed_link("gripper", 26);
        color(link_color) solid_link(joint_position("gripper"), frame, 15);
        color(link_color) translate(frame) jaw_finger(62, 15);
    }
}

module gripper_link() {
    gripper_printed();
    if (show_lids)
        color(lid_color) at_servo("gripper") servo_lid_local();
    if (show_motors)
        color(motor_color) at_servo("gripper") motor_local();
    at_joint("gripper", q[5]) moving_jaw();
}

module wrist_chain() {
    fitted_link("wrist_roll", 27);
    at_joint("wrist_roll", q[4]) gripper_link();
}

module lower_arm_chain() {
    fitted_link("wrist_flex");
    at_joint("wrist_flex", q[3]) wrist_chain();
}

module upper_arm_chain() {
    fitted_link("elbow_flex");
    at_joint("elbow_flex", q[2]) lower_arm_chain();
}

module shoulder_chain() {
    fitted_link("shoulder_lift");
    at_joint("shoulder_lift", q[1]) upper_arm_chain();
}

module arm() {
    base_column();
    at_joint("shoulder_pan", q[0]) shoulder_chain();
}

module compact_outline(layer) {
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
        translate([0, 0, 2]) horn_pattern(4.2);
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
else if (part == "base_column") base_column_printed();
else if (part == "shoulder") printed_link("shoulder_lift");
else if (part == "upper_arm") printed_link("elbow_flex");
else if (part == "lower_arm") printed_link("wrist_flex");
else if (part == "wrist") printed_link("wrist_roll", 27);
else if (part == "gripper") gripper_printed();
else if (part == "moving_jaw") moving_jaw();
else if (part == "servo_lid") servo_lid_local();
else if (part == "clearance_coupon") clearance_coupon();
else if (part == "horn_coupon") horn_coupon();
else assert(false, str("unknown part: ", part));
