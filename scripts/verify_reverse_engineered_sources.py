"""Surface-check the generated reverse-engineered print sources."""

from pathlib import Path

import Mesh

from scripts.compare_reauthored_assets import aligned_comparison
from scripts.reverse_engineered import MANIFESTS, entries, parts


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
            result = aligned_comparison(Mesh.Mesh(str(original)), Mesh.Mesh(str(generated)))
            if result["status"] == "fail":
                raise RuntimeError(
                    f"{entry['id']}: surface mismatch (max={result['max_surface_error_mm']:.3f} mm, "
                    f"p95={result['p95_surface_error_mm']:.3f} mm)"
                )
            print(
                f"{entry['id']}: pass max={result['max_surface_error_mm']:.3f} mm "
                f"p95={result['p95_surface_error_mm']:.3f} mm"
            )
