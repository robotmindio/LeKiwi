# Published accessory sources

This directory contains FreeCAD documents only when an exact, redistributable
editable source is already published with LeKiwi. They are intentionally kept
outside the URDF assembly: webcam mounts are alternative camera hardware, not
the Arducam configuration represented in `LeKiwi.FCStd`.

| Accessory | Published source | FreeCAD document | Source kind |
| --- | --- | --- | --- |
| Webcam base mount | `3DPrintMeshes/webcam_mount/webcam_mount.step` | `webcam_base_mount.FCStd` | Imported STEP BREP |
| Webcam wrist mount | `3DPrintMeshes/webcam_mount/webcam_mount_wrist.step` | `webcam_wrist_mount.FCStd` | Imported STEP BREP |
| SO-100 webcam gripper insert | `cad/upstream/SO-ARM100/STEP/SO100/Follower_Specific/Wrist_Roll_08c v1.step` + editable M3 boss | `so100_gripper_cam_mount_insert.FCStd` | SO-ARM100 STEP derivative |

Build or reset those documents, then verify that they still match their
corresponding print STLs:

```sh
./scripts/build_accessory_sources.sh
./scripts/verify_accessory_sources.sh
```

These are editable Open STEP BREP documents in FreeCAD's Part workbench. The
SO-100 derivative keeps its upstream wrist-roll BREP and its M3 camera-mount
boss as a separate editable cylinder/fuse. The upstream wrist-roll revision is
within 0.191% by volume but differs by 2.325% in bounding box from LeKiwi's
legacy print, so this derivative is not presented as an exact reconstruction.
None are claimed to reconstruct the original parametric feature history.

## External or non-identical sources

| Accessory family | Source found | Why it remains external |
| --- | --- | --- |
| Raspberry Pi case top and bottom | [Printables model 605060](https://www.printables.com/model/605060-raspberry-pi-5-case-wpower-button-v2) publishes STEP files | Its CC BY-NC terms cannot be silently relicensed under this repository's Apache-2.0 license. The LeKiwi STLs are described as modified from that model, so the public STEP is not assumed to be an exact replacement either. |
| Standard SO-100/SO-101 arm | [TheRobotStudio/SO-ARM100](../upstream/SO-ARM100/) publishes Apache-2.0 STEP sources | The repository is pinned as a Git submodule. The SO-100 follower source is checked by `scripts/verify_arm_sources.sh`; `modified_base_arm` is not verified as an exact upstream part. |
| VEX-derived wheel hub | VEX provides downloadable CAD for its parts | `servo_wheel_hub.stl` is documented as modified from a VersaHub, not as an unmodified vendor part. No exact Apache-compatible source for the LeKiwi derivative was established, so the vendor file is not vendored here. |

## Reauthoring candidates with no exact editable source located

The search covered the LeKiwi repository history, its Fusion archive, and the
published upstream projects above. The following print assets still need a
native reauthoring if they are to become editable FreeCAD sources:

- `3DPrintMeshes/battery_mount_eu.stl` and `5v_specific/5v_power_bank_holder.stl`
- `3DPrintMeshes/drive_motor_mount_v2.stl`
- `3DPrintMeshes/modified_base_arm.stl`, `jetson_holder.stl`, and `wrist_camera_mount.stl`
- `3DPrintMeshes/wired_specific/cable_holder v0.stl` and `wired_specific/usb_connector_case v1.stl`
- `3DPrintMeshes/dynamixel_specific/Dynamixel_omni_wheel_mount v2.stl`, `center_triangular_insert.stl`, `dynamixel_drive_motor_mount.stl`, `dynamixel_kiwi_servo_mount.stl`, `dynamixel_modified_base_arm.stl`, `dynamixel_wheel_hub .stl`, `follower_base.stl`, `modified_static_side_with_mount.stl`, `pi_case_bottom.stl`, and `webcam_base_mount.stl`

`drive_motor_mount.stl`, `servo_wheel_hub.stl`, `servo_controller_mount.stl`,
`battery_mount.stl`, `base_camera_mount.stl`, and
`dynamixel_specific/lipo_battery_mount.stl` correspond to existing native
URDF sources, so they are not missing-source candidates.

The `drive_motor_mount_v2.stl` and `wrist_camera_mount.stl` print revisions do
not match their older URDF counterparts, so the current native URDF sources
must not be presented as editable sources for those two files.

The core URDF source files in `cad/parts/` are tracked separately. Their
current geometric-fidelity audit is recorded in
`cad/validation/reauthored_asset_comparison.json`; all twelve native link
instances pass its sampled surface criterion. That validation does not extend
to the alternative accessory prints listed above.

## Core native-source fidelity

The two laser plates and all six native printed sources pass the strict
bidirectional sampled surface audit against their corresponding original URDF
meshes. The maximum measured deviation is 0.056 mm and the largest 95th
percentile is 0.034 mm.
