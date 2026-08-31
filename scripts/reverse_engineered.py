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
