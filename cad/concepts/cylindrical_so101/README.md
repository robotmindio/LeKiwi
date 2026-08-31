# Cylindrical SO-101 concept

This is an isolated OpenSCAD redesign; nothing here is consumed by the current
FreeCAD, URDF, Xacro, ROS, or manufacturing export pipelines.

`generate_kinematics.py` copies the six official SO-101 joint origins and limits,
verifies their local-Z axes, and copies the LeKiwi arm mount and functional base
mounts into generated OpenSCAD constants. The design therefore changes only
structure and appearance, not the kinematic chain. Circular joint covers are
rotationally symmetric at every axis, so they add no geometric joint stop within
the official ranges.

The arm uses hollow 32 mm tubes, repeated horn hubs and motor cradles, and one
split motor cover. Each link starts at the moving horn and ends at the next
motor body, matching the physical serial chain. The hub uses the official STEP's
24 mm horn boss and four M3 holes on a 9.9 mm square. Motors slide axially from
their cradles and are enclosed except for an underside cable route and protected
vent slots; two accessible M3 fasteners release either cover half without
disturbing the neighboring link.

The base intersects a convex structural outline with the validated lower and
upper DXFs. This keeps the original holes at every current functional component
placement while dropping unused grid holes outside the new outline. A 3 mm skin,
7 mm perimeter/rib section, radial load paths, and local mount pads reduce
material without reducing the current maximum section depth. Because the camera,
wheel and standoff coordinates are retained, the overall X/Y span cannot shrink
materially; moving those mounts is the tradeoff required for a smaller bounding
box. The current parameters reduce projected plate area by 12.5% and lower-plate
material volume by 41.6% versus the current solid 7 mm profile; these are geometric
figures, not an untested strength claim.

## Build and inspect

```sh
cd cad/concepts/cylindrical_so101
python3 generate_kinematics.py
python3 verify_design.py
openscad design.scad
```

Set `part` in the Customizer or on the command line, for example:

```sh
openscad -o upper_arm.stl -D 'part="upper_arm"' design.scad
openscad -o assembly.png --imgsize=1400,1000 --viewall --autocenter design.scad
```

Print `clearance_coupon` and `horn_coupon` first and tune `fit_clearance`. Before
load-bearing use, confirm the purchased STS3215 and horn revision, cable bend
radius and assembled joint gaps; then perform a static proof load and a full-range
powered sweep at low torque. Material-dependent strength is intentionally not
claimed from CAD alone.
