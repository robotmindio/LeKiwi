.PHONY: attach-cad-part build-accessory-sources build-laser-plate-sources \
	build-native-part-sources compare-reauthored-assets export-cad-meshes \
	import-step-reference link-base-plate-sources link-native-part-sources \
	seed-robot-metadata verify-accessory-sources verify-cad-migration \
	verify-laser-plate-sources verify-manufacturing-sources verify-mesh-integrity \
	verify-native-part-sources verify-reverse-engineered-sources

# Named targets for the one-line FreeCAD script invocations that used to be
# their own trivial scripts/*.sh wrappers. Each wrapper only forwarded to
# run_freecad_script.sh (or, for the two plain-Python targets, to python3)
# with fixed or passed-through arguments; see cad/README.md for when to run
# each one. Use ARGS="..." for the targets that take arguments.

attach-cad-part:
	./scripts/run_freecad_script.sh scripts/attach_cad_part.py $(ARGS)

build-accessory-sources:
	./scripts/run_freecad_script.sh scripts/build_accessory_sources.py

build-laser-plate-sources:
	./scripts/run_freecad_script.sh scripts/build_laser_plate_sources.py

build-native-part-sources:
	./scripts/run_freecad_script.sh scripts/build_native_part_sources.py

compare-reauthored-assets:
	./scripts/run_freecad_script.sh scripts/compare_reauthored_assets.py $(ARGS)

export-cad-meshes:
	./scripts/run_freecad_script.sh scripts/export_cad_meshes.py cad/assembly/LeKiwi.FCStd URDF/meshes/reauthored

import-step-reference:
	./scripts/run_freecad_script.sh scripts/import_step_reference.py reference/fusion/LeKiwi.stp cad/assembly/LeKiwi_reference.FCStd

link-base-plate-sources:
	./scripts/run_freecad_script.sh scripts/link_base_plate_sources.py

link-native-part-sources:
	./scripts/run_freecad_script.sh scripts/link_native_part_sources.py

seed-robot-metadata:
	./scripts/run_freecad_script.sh scripts/seed_robot_metadata.py cad/assembly/LeKiwi_reference.FCStd URDF/LeKiwi.baseline.urdf cad/assembly/LeKiwi.FCStd

verify-accessory-sources:
	./scripts/run_freecad_script.sh scripts/verify_accessory_sources.py

verify-cad-migration:
	./scripts/run_freecad_script.sh scripts/verify_cad_migration.py URDF/LeKiwi.baseline.urdf cad/reference_mapping.json URDF/meshes/reauthored

verify-laser-plate-sources:
	./scripts/run_freecad_script.sh scripts/verify_laser_plate_sources.py

verify-manufacturing-sources:
	python3 scripts/verify_manufacturing_sources.py

verify-mesh-integrity:
	./scripts/run_freecad_script.sh scripts/verify_mesh_integrity.py

verify-native-part-sources:
	./scripts/run_freecad_script.sh scripts/verify_native_part_sources.py

verify-reverse-engineered-sources:
	python3 -m scripts.build_reverse_engineered_sources
	./scripts/run_freecad_script.sh scripts/verify_reverse_engineered_sources.py
