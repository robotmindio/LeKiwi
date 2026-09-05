# Robot model consistency

Completed: sensor mounts attached to the upper plate; SO-101 base derived from
the assembly shoulder datum; native wrist-flex part connected in metre units;
official arm meshes refreshed on export.

Verified: native wrist STEP-fidelity checks, shoulder centre/pan/lift-axis preservation and
propagation of a 20 mm assembly edit, Xacro semantics, chassis mesh fidelity,
native part trees and accessory source checks. Input/output manifest checks
reject edits without regeneration. Full `verify_robot.sh` is finishing the
remaining reference/manufacturing checks.

Next: vendor this revision into cleanroom, verify the installed/live description,
inspect the physical placements, and guide the user through SO-101 recalibration.
Physical calibration and measured Astra optical-centre correction remain pending.

The user's pre-existing `media/assembly_imgs/IMG_9250.jpg` change is unrelated
and has not been staged. Remove this file after final model verification.
