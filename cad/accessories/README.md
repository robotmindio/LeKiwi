# Published accessory sources

This directory contains FreeCAD documents only when an exact, redistributable
editable source is already published with LeKiwi. They are intentionally kept
outside the URDF assembly: webcam mounts are alternative camera hardware, not
the Arducam configuration represented in `LeKiwi.FCStd`.

| Accessory | Published source | FreeCAD document | Source kind |
| --- | --- | --- | --- |
| Webcam base mount | `3DPrintMeshes/webcam_mount/webcam_mount.step` | `webcam_base_mount.FCStd` | Imported STEP BREP |
| Webcam wrist mount | `3DPrintMeshes/webcam_mount/webcam_mount_wrist.step` | `webcam_wrist_mount.FCStd` | Imported STEP BREP |

Build or reset those documents, then verify that they still match their
corresponding print STLs:

```sh
./scripts/build_accessory_sources.sh
./scripts/verify_accessory_sources.sh
```

These are editable Open STEP BREP documents in FreeCAD's Part workbench. They
are not claimed to reconstruct the original parametric feature history.

## Sources found but not vendored

| Accessory family | Source found | Why it remains external |
| --- | --- | --- |
| Raspberry Pi case top and bottom | [Printables model 605060](https://www.printables.com/model/605060-raspberry-pi-5-case-wpower-button-v2) publishes STEP files | Its CC BY-NC terms cannot be silently relicensed under this repository's Apache-2.0 license. The LeKiwi STLs are described as modified from that model, so the public STEP is not assumed to be an exact replacement either. |
| Standard SO-100/SO-101 arm | [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100/tree/main/STEP) publishes Apache-2.0 STEP sources | It is an independently maintained robot project; retaining it as an external dependency avoids duplicating its large source tree. The LeKiwi `modified_base_arm` and webcam gripper insert are not verified as exact upstream parts. |
| VEX-derived wheel hub | VEX provides downloadable CAD for its parts | `servo_wheel_hub.stl` is documented as modified from a VersaHub, not as an unmodified vendor part. No exact Apache-compatible source for the LeKiwi derivative was established, so the vendor file is not vendored here. |

## Reauthoring candidates with no exact editable source located

The search covered the LeKiwi repository history, its Fusion archive, and the
published upstream projects above. The following print assets still need a
native reauthoring if they are to become editable FreeCAD sources:

- `3DPrintMeshes/battery_mount_eu.stl` and `5v_specific/5v_power_bank_holder.stl`
- `3DPrintMeshes/drive_motor_mount_v2.stl`
- `3DPrintMeshes/modified_base_arm.stl`, `jetson_holder.stl`, and `wrist_camera_mount.stl`
- `3DPrintMeshes/webcam_mount/so100_gripper_cam_mount_insert.stl`
- `3DPrintMeshes/wired_specific/cable_holder v0.stl` and `wired_specific/usb_connector_case v1.stl`
- `3DPrintMeshes/dynamixel_specific/Dynamixel_omni_wheel_mount v2.stl`, `center_triangular_insert.stl`, `dynamixel_drive_motor_mount.stl`, `dynamixel_kiwi_servo_mount.stl`, `dynamixel_modified_base_arm.stl`, `dynamixel_wheel_hub .stl`, `follower_base.stl`, `modified_static_side_with_mount.stl`, `pi_case_bottom.stl`, and `webcam_base_mount.stl`

`drive_motor_mount.stl`, `servo_wheel_hub.stl`, `servo_controller_mount.stl`,
`battery_mount.stl`, `base_camera_mount.stl`, and
`dynamixel_specific/lipo_battery_mount.stl` correspond to existing native
URDF sources. They belong in the accuracy-rework queue below, not the
missing-source queue.

The `drive_motor_mount_v2.stl` and `wrist_camera_mount.stl` print revisions do
not match their older URDF counterparts, so the current native URDF sources
must not be presented as editable sources for those two files.

The core URDF source files in `cad/parts/` are tracked separately. Their
current geometric-fidelity audit is recorded in
`cad/validation/reauthored_asset_comparison.json`; matching bounds and volume
does not by itself establish surface equivalence.

## Existing native sources that still need accuracy rework

The strict audit currently passes the two laser plates only. The native
printed sources for the drive mount, omni-wheel mount, servo-controller mount,
LiPo mount, base camera mount, and wrist camera mount remain editable, but
their generated URDF assets are not yet geometry-equivalent to their original
meshes. Rework those six sources before treating the core printed assembly as
a faithful open replacement.
