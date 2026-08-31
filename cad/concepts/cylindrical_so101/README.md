# Cylindrical SO-101 concept

This is an isolated OpenSCAD redesign; nothing here is consumed by the current
FreeCAD, URDF, Xacro, ROS, or manufacturing export pipelines.

`generate_kinematics.py` copies the six official SO-101 joint origins and limits,
verifies their local-Z axes, and copies the LeKiwi arm mount and functional base
mounts into generated OpenSCAD constants. It also extracts each STS3215 pose and
checks that the canonical 12.5 × 0 × 18.7 mm shaft offset lands on the matching
joint axis. The design therefore changes structure and appearance, not the
kinematic chain.

The arm is assembled bottom-up from one repeated form: a 32 mm horn flange, a
hollow 30 mm round link, and a rounded pod around the next servo. Every moving
flange has the same horn-side standoff, so it clears the parent pod without
moving either joint frame. The rectangular cavity reacts motor torque; the motor
slides out through a rear cap retained by two accessible M3 screws and heat-set
inserts. The same cap is used at all six motors. The flange uses the SO-101 H25T
24 mm horn recess and four M3 holes at 7 mm radius.

The base intersects a convex structural outline with the validated lower and
upper DXFs. This keeps the original holes at every current functional component
placement while dropping unused grid holes outside the new outline. A 3 mm skin,
7 mm perimeter/rib section, radial load paths, and local mount pads reduce
material without reducing the current maximum section depth. Because the camera,
wheel and standoff coordinates are retained, the overall X/Y span cannot shrink
materially; moving those mounts is the tradeoff required for a smaller bounding
box. The current parameters reduce projected plate area by 12.5% and lower-plate
material volume by 41.8% versus the current solid 7 mm profile; these are geometric
figures, not an untested strength claim.

The moving printed parts, including five service caps, use 40.4% less modeled
material volume than the corresponding upstream SO-101 moving parts. This is a
geometry comparison, not a mass claim for dissimilar materials or print setups.

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

Print `clearance_coupon`, `horn_coupon`, and one `servo_lid` first and tune
`fit_clearance`. Before load-bearing use, confirm the purchased STS3215 and horn
revision, base attachment, cable bend radius and assembled joint gaps; then
perform a static proof load and a joint-by-joint powered sweep at low torque.
The official scalar limits are preserved, but neither the upstream arm nor this
concept promises that every combination of simultaneous limit angles is
collision-free. Material-dependent strength is intentionally not claimed from
CAD alone.
