// Measured LeKiwi overlays. Regenerate layout with build_robotskin_surfaces.sh.
include <../upstream/RobotSkin/scad/lib/robotskin.scad>
include <../generated/robotskin/layout.scad>

surface = "top"; // top, floor, ceiling; all exports lie flat with ports facing up.
$fn = 32;
assert(surface == "top" || surface == "floor" || surface == "ceiling");
layout = layouts[surface == "top" ? 0 : surface == "floor" ? 1 : 2];

module overlay() {
  difference() {
    linear_extrude(RM_PLATE_T)
      difference() {
        offset(delta=-0.5) polygon(layout[0]);
        for (cut=layout[1]) polygon(cut);
        for (post=layout[2]) translate([post[0],post[1]]) circle(r=post[2]);
      }
    for (p=layout[4]) translate([p[0],p[1],RM_PLATE_T])
      mirror([0,0,1]) port_cut();
    for (p=layout[3]) translate([p[0],p[1],-RM_EPS])
      cylinder(h=RM_PLATE_T+2*RM_EPS,d=RM_M3_CLEARANCE);
  }
}

// Flip Y in the print frame, so turning the ceiling over restores chassis XY.
if (surface == "ceiling") mirror([0,1,0]) overlay();
else overlay();
