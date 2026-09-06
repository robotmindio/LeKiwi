# Part 8 restart

Completed: removed the rejected simplified model. Its source remains in Git
history; previous generated comparison files and the simplified STL are archived
under `cad/generated/rejected-part8/`.

Reference: the pinned upstream `STEP/SO101/Wrist_Roll_Pitch_SO101.step`, loaded by
`so101_wrist.load_part("flex_body")`. Exported directly in millimetres to
`cad/generated/so101_part8_upstream_original.stl`. The native `so101_part8.py`
is a reconstruction and must not be called the exact upstream original.

Verified: the upstream reference is one valid solid, volume 32312.812243757595
mm³. The earlier zero-difference result compared only two versions of the
rejected simplified model; it did not establish compatibility with the original.

Pending: clarify whether to simplify native code while preserving the original
shape, or redesign the physical shape. For a physical redesign, establish print
material, nozzle and support requirements, preserve mounting/contact surfaces,
and check assembly motion and structural/printing consequences.

Next: establish this scope before creating another candidate. Direct boolean
subtractions between the upstream STEP and native reconstruction produced
inconsistent volume accounting; investigate before using them as validation.
No replacement design or mechanical/printability validation is complete.
