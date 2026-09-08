# Physical chassis corrections

- Completed: six existing rods repositioned to the operator-marked screw holes,
  at (±100, 0) and (±60, ±80) mm; upper plate and arm world placement preserved.
- Verified: all six locations match holes in both plates; CAD and joint poses agree.
- Exported: Xacro and model manifest updated; Xacro semantics and arm-mount checks pass.
- Completed: native v2 cage reconstructed from the supplied official STL,
  47.5 × 34.8 × 45.5 mm installed size; sampled maximum deviation 0.211 mm.
- Updated: all three cage/servo joint poses and visible wheel assemblies;
  skin generator uses active geometry and 4 mm per-side motor clearance.
- Verified: native feature trees; all 12 chassis fastener axes; Xacro poses;
  all 11 active native mesh exports pass the strict surface audit.
- Regenerated: top/floor/ceiling skins (4 mm per-side motor clearance), review
  assembly, full-build/wheel/floor images. All three skin meshes pass validation.
- Known reference caveat: servo corners intersect the official v2 cage by less
  than 1 mm³ per unit; preserve the supplied mount and physically check fit.
- Pending: full isolated robot regression suite is running; review its result,
  remove this WIP, refresh/check the manifest, then commit and push final state.
