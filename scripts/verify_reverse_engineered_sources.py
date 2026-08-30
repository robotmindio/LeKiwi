"""Surface-check the generated reverse-engineered print sources."""

import json
import runpy
from pathlib import Path

import Mesh


MANIFESTS = tuple(sorted(Path("cad/reverse_engineered").glob("*/parts.json")))
compare = runpy.run_path("scripts/compare_reauthored_assets.py")


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


def reference_component(part):
    if not part.get("original_component_signature"):
        return Path(part["original"])
    output = Path(part["output"])
    return output.with_name(output.stem + "_original.stl")


for manifest in MANIFESTS:
    for part in parts(manifest):
        for entry in entries(part):
            output = entry.get("output")
            if not output:
                continue
            original, generated = reference_component(entry), Path(output)
            if not original.is_file() or not generated.is_file():
                raise RuntimeError(f"{entry['id']}: missing original or generated mesh")
            result = compare["aligned_comparison"](Mesh.Mesh(str(original)), Mesh.Mesh(str(generated)))
            if result["status"] == "fail":
                raise RuntimeError(
                    f"{entry['id']}: surface mismatch (max={result['max_surface_error_mm']:.3f} mm, "
                    f"p95={result['p95_surface_error_mm']:.3f} mm)"
                )
            print(
                f"{entry['id']}: pass max={result['max_surface_error_mm']:.3f} mm "
                f"p95={result['p95_surface_error_mm']:.3f} mm"
            )
