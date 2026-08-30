"""Build reverse-engineered OpenSCAD sources into ignored validation meshes."""

import json
import re
import subprocess
from pathlib import Path

import trimesh

MANIFESTS = tuple(sorted(Path("cad/reverse_engineered").glob("*/parts.json")))


def parts(path):
    data = json.loads(path.read_text())
    return data.get("parts", data) if isinstance(data, dict) else data


def entries(part):
    components = part.get("component_validations")
    if not components:
        yield part
        return
    for component in components:
        yield {**part, **component}


def source_path(part):
    source = part.get("source")
    if isinstance(source, str):
        return Path(source)
    if isinstance(source, dict) and "path" in source:
        return Path(source["path"])
    return None


def selector(part):
    source = part.get("source")
    return part.get("selector") or (source.get("selector") if isinstance(source, dict) else None)


def reference_component(part):
    signature = part.get("original_component_signature")
    if not signature:
        return None
    mesh = trimesh.load_mesh(part["original"], process=True)
    components = mesh.split(only_watertight=signature["watertight"])

    def matches_signature(component):
        observed = (
            component.is_watertight == signature["watertight"]
            and len(component.faces) == signature["face_count"]
            and len(component.vertices) == signature["vertex_count"]
            and abs(component.volume - signature["volume_mm3"]) < 1e-5
        )
        return observed and all(
            abs(actual - expected) < 1e-5
            for actual_row, expected_row in zip(component.bounds, signature["bounds_mm"])
            for actual, expected in zip(actual_row, expected_row)
        )

    matching_components = [component for component in components if matches_signature(component)]
    if len(matching_components) != 1:
        raise RuntimeError(f"{part['id']}: component signature matched {len(matching_components)} original bodies")
    output = Path(part["output"]).with_name(Path(part["output"]).stem + "_original.stl")
    matching_components[0].export(output)
    return output


for manifest in MANIFESTS:
    for part in parts(manifest):
        for entry in entries(part):
            source = source_path(entry)
            output = entry.get("output")
            if not source or source.suffix != ".scad" or not output:
                continue
            if not source.is_file():
                raise RuntimeError(f"{entry['id']}: missing OpenSCAD source {source}")
            if re.search(r'import\s*\([^)]*\.stl', source.read_text(), re.IGNORECASE):
                raise RuntimeError(f"{entry['id']}: source imports a rendered STL")
            output = Path(output)
            output.parent.mkdir(parents=True, exist_ok=True)
            command = ["openscad", "-o", str(output.resolve())]
            if selector(entry) is not None:
                command += ["-D", f'part="{selector(entry)}"']
            command.append(str(source.resolve()))
            subprocess.run(command, cwd=source.parent, check=True)
            reference = reference_component(entry)
            label = f" (reference {reference})" if reference else ""
            print(f"built {entry['id']}: {output}{label}")
