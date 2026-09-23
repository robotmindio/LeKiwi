import json
from pathlib import Path


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


def original_component_path(output):
    """Path to the isolated original-body reference next to a generated OUTPUT.

    Shared by build_reverse_engineered_sources.py (which writes it) and
    verify_reverse_engineered_sources.py (which reads it) so the naming
    convention lives in one place.
    """
    output = Path(output)
    return output.with_name(output.stem + "_original.stl")
