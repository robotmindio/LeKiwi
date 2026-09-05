"""A committed source edit must invalidate an older generated model."""

import json
from pathlib import Path
import tempfile
import unittest

from scripts.model_manifest import ROOT, MANIFEST, check, snapshot


class ModelManifestTest(unittest.TestCase):
    def test_source_and_output_changes_require_regeneration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for group in snapshot(ROOT).values():
                for name in group:
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("fixture")
            for name in ("cad/cadquery/so101_part8.py", "URDF/LeKiwi.urdf.xacro"):
                (root / MANIFEST).write_text(json.dumps(snapshot(root)))
                check(root)
                (root / name).write_text("changed")
                with self.assertRaisesRegex(ValueError, "model needs"):
                    check(root)


if __name__ == "__main__":
    unittest.main()
