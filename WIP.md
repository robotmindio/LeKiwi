# Accuracy rework checkpoint

- Completed: rebuilt the servo-controller mount, LiPo tray, drive mount, base camera mount, and wrist camera mount from source feature geometry; the wrist mount retains only its exact external XRef clearance as a hidden cut tool.
- Next: rebuild the omni-wheel mount from its canonical URDF mesh geometry.
- Verified: controller (0.029 mm max, 0.017 mm p95), LiPo tray (0.013 mm max, 0.006 mm p95), all three drive-mount instances (0.015 mm max, 0.005 mm p95), base camera mount (0.026 mm max, 0.012 mm p95), and wrist mount (0.038 mm max, 0.010 mm p95) pass the bidirectional surface audit.
- Pending: run the complete strict audit and update the migration documentation after every native printed part passes.
