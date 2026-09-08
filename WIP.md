# Physical chassis corrections

- Completed: six existing rods repositioned to the operator-marked screw holes,
  at (±100, 0) and (±60, ±80) mm; upper plate and arm world placement preserved.
- Verified: all six locations match holes in both plates; CAD and joint poses agree.
- Exported: Xacro and model manifest updated; Xacro semantics and arm-mount checks pass.
- Pending: motor-stand source resize to 50 × 37 mm. Awaiting a side view/confirmation
  whether the measurement describes the top flange or chassis-contact footprint.
- Next: correct the native motor-stand feature tree and its three placements,
  validate/export, then regenerate RobotSkin surfaces and images from the corrected model.
- Existing generated RobotSkin skins still contain the previous pillar layout.
