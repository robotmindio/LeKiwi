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
    fusion_members = set(archive.namelist())
fusion_names = {
    item["friendlyName"]
    for graph in design["designDescription"]["designGraphs"]
    for item in graph["designObjects"]
}


def check_reference(part, key, value):
    filename, _, fragment = value.partition("#")
    path = Path(filename)
    if path == Path("reference/fusion/LeKiwi.f3z"):
        if fragment not in fusion_names and fragment not in fusion_members:
            raise SystemExit(f"missing Fusion component {fragment!r}")
    elif not path.is_file():
        raise SystemExit(f"missing {key} for {part['id']}: {value}")
    elif fragment and path.name == "parts.json":
        data = json.loads(path.read_text())
        records = data.get("parts", data) if isinstance(data, dict) else data
        if fragment not in {record["id"] for record in records}:
            raise SystemExit(f"missing source record {fragment!r} in {path}")
    elif fragment and path.suffix == ".json" and fragment not in json.loads(path.read_text()):
        raise SystemExit(f"missing validation record {fragment!r} in {path}")


for part in parts + manifest["additional_prints"] + manifest["flat_parts"]:
    for key in ("source", "solid_source", "reference", "validation", "build", "dxf", "pdf"):
        value = part.get(key)
        if not value:
            continue
        check_reference(part, key, value)
    for value in part.get("cut_outputs", []):
        if not Path(value).is_file():
            raise SystemExit(f"missing cut output for {part['id']}: {value}")
    if "stl" not in part:
        continue
    if part.get("source_state") == "stl_only" or not part.get("source"):
        raise SystemExit(f"{part['id']}: print has no editable source")
    if part["fidelity"] not in {
        "surface_validated",
        "component_surface_validated",
        "compositional_validated",
    }:
        raise SystemExit(f"{part['id']}: unvalidated print fidelity {part['fidelity']!r}")

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
