$fn = 64;

plate = [80, 60, 8];
corner_radius = 4;
deck_hole_spacing = [40, 40];
deck_hole_d = 3.6;
deck_head_d = 6.5;
deck_head_depth = 3;
camera_hole_d = 6.8;       // M6 or 1/4-inch screw clearance; use the camera's actual thread.
camera_head_d = 11;
camera_head_depth = 3.8;   // M6 button-head recess.
camera_foot_width = 60;
epsilon = 0.1;

assert(plate[0] >= camera_foot_width + 2 * corner_radius,
       "plate must support the Astra's 60 mm foot");
assert(deck_hole_spacing[0] < plate[0] - deck_head_d &&
       deck_hole_spacing[1] < plate[1] - deck_head_d,
       "deck screw heads need edge clearance");
assert(camera_head_depth < plate[2],
       "camera screw recess must leave a load-bearing top wall");

module rounded_plate(size, radius) {
  hull()
    for (x = [-size[0] / 2 + radius, size[0] / 2 - radius],
         y = [-size[1] / 2 + radius, size[1] / 2 - radius])
      translate([x, y, 0]) cylinder(h = size[2], r = radius);
}

difference() {
  rounded_plate(plate, corner_radius);

  for (x = [-deck_hole_spacing[0] / 2, deck_hole_spacing[0] / 2],
       y = [-deck_hole_spacing[1] / 2, deck_hole_spacing[1] / 2]) {
    translate([x, y, -epsilon])
      cylinder(h = plate[2] + 2 * epsilon, d = deck_hole_d);
    translate([x, y, plate[2] - deck_head_depth])
      cylinder(h = deck_head_depth + epsilon, d = deck_head_d);
  }

  translate([0, 0, -epsilon])
    cylinder(h = plate[2] + 2 * epsilon, d = camera_hole_d);
  translate([0, 0, -epsilon])
    cylinder(h = camera_head_depth + epsilon, d = camera_head_d);
}
