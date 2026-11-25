#!/usr/bin/env python3
"""Keep documentation in sync with validation constants."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate  # noqa: E402


class DocsConsistency(unittest.TestCase):
    def test_schema_lists_every_scope(self):
        text = (ROOT / "_schema.md").read_text(encoding="utf-8")
        for code in validate.SCOPES:
            with self.subTest(scope=code):
                self.assertIn(f"`{code}`", text, f"_schema.md не описывает раздел {code}")


if __name__ == "__main__":
    unittest.main()
