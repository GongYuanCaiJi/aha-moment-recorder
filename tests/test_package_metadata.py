from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

import build_backend


class PackageMetadataTests(unittest.TestCase):
    def test_wheel_contains_public_project_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = build_backend.build_wheel(directory)
            wheel_path = Path(directory) / filename
            with zipfile.ZipFile(wheel_path) as archive:
                metadata = archive.read("aha_moment_recorder-0.1.0.dist-info/METADATA").decode()

        self.assertIn("Author: GongYuanCaiJi", metadata)
        self.assertIn("License: MIT", metadata)
        self.assertIn("Project-URL: Repository, https://github.com/GongYuanCaiJi/aha-moment-recorder", metadata)
        self.assertIn("Project-URL: Security, https://github.com/GongYuanCaiJi/aha-moment-recorder/security/policy", metadata)
        self.assertIn("Classifier: Development Status :: 3 - Alpha", metadata)
        self.assertIn("Classifier: Programming Language :: Python :: 3.13", metadata)


if __name__ == "__main__":
    unittest.main()
