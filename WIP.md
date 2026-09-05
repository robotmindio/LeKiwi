# Robot model consistency

Completed: sensor mounts attached to the upper plate; SO-101 base derived from
the assembly shoulder datum; native wrist-flex part connected in metre units;
official arm meshes refreshed on export.

Operator correction: forward is the arm/fixed-camera side. SO-101 now faces
outward (+Y CAD / +X ROS), preserving its shoulder centre with a fixed half-turn.
Removed the still-exported Pi case and moved the lidar to its rear screw pair;
all four RobotSkin fasteners match actual plate holes. The scan centre is
135 mm rearward and 5 mm left in ROS. Astra belongs on the left side as pictured;
its 44 mm bracket spacing does not match the nearby 40 mm plate pair. Asked
whether it uses existing or newly drilled holes before assigning an exact pose.

Verified: native wrist STEP-fidelity checks, shoulder centre/pan/lift-axis preservation and
propagation of a 20 mm assembly edit, Xacro semantics, chassis mesh fidelity,
native part trees and accessory source checks. Input/output manifest checks
reject edits without regeneration. Full `verify_robot.sh` passed, including
reference/manufacturing checks (32 print assets, 2 flat parts, 32 sourced parts).

Vendored into cleanroom and verified against the managed install and live
robot_state_publisher. Next: inspect physical placements and guide SO-101
recalibration once robot-1 is online (currently offline). Physical calibration
and measured Astra optical-centre correction remain pending; cleanroom/WIP.md
tracks the remaining runtime verification.

Latest operator correction: export, Xacro semantics, arm datum/outward direction,
lidar-to-plate hole alignment, manifest tests and CAD migration checks passed.
Vendor/deploy this corrected revision next; earlier live verification predates it.

The user's pre-existing `media/assembly_imgs/IMG_9250.jpg` change is unrelated
and has not been staged. Remove this file after final model verification.
