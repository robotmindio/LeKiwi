"""Check that the manufacturing index covers every shipped print and source."""

import json
import zipfile
from pathlib import Path


manifest = json.loads(Path("manufacturing/parts.json").read_text())
parts = manifest["prints"]
stls = {path.as_posix() for path in Path("3DPrintMeshes").rglob("*.stl")}
listed = {part["stl"] for part in parts}
if listed != stls:
    raise SystemExit(f"print inventory mismatch: missing={sorted(stls - listed)}, extra={sorted(listed - stls)}")

with zipfile.ZipFile("reference/fusion/LeKiwi.f3z") as archive:
    design = json.loads(archive.read("DesignDescription.json"))
fusion_names = {
    item["friendlyName"]
    for graph in design["designDescription"]["designGraphs"]
    for item in graph["designObjects"]
}

for part in parts + manifest["additional_prints"] + manifest["flat_parts"]:
    for key in ("source", "reference", "flat_source", "dxf", "pdf"):
        value = part.get(key)
        if not value:
            continue
        if value.startswith("reference/fusion/LeKiwi.f3z#"):
            name = value.partition("#")[2]
            if name not in fusion_names:
                raise SystemExit(f"missing Fusion component {name!r}")
        elif not Path(value).is_file():
            raise SystemExit(f"missing {key} for {part['id']}: {value}")
    for value in part.get("cut_outputs", []):
        if not Path(value).is_file():
            raise SystemExit(f"missing cut output for {part['id']}: {value}")
    if part.get("source_state") == "stl_only" and part["fidelity"] != "none":
        raise SystemExit(f"{part['id']}: STL-only parts cannot claim fidelity")

source_data = json.loads(Path("manufacturing/sourced-parts.json").read_text())
source_bom = source_data["parts"]
ids = {part["id"] for part in source_bom}
if len(ids) != len(source_bom):
    raise SystemExit("duplicate sourced-part ID")
for part in source_bom:
    if not part.get("manufacturer") or not (part.get("manufacturer_part_number") or part.get("supplier_sku")):
        raise SystemExit(f"incomplete sourced part: {part['id']}")
for name, configuration in source_data["configurations"].items():
    missing = set(configuration) - ids
    if missing:
        raise SystemExit(f"{name}: unknown sourced parts {sorted(missing)}")

print(f"validated {len(parts)} print assets, {len(manifest['flat_parts'])} flat parts, and {len(source_bom)} sourced parts")
