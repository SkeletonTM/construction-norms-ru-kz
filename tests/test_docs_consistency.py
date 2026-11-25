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

    def test_find_scope_help_has_no_unknown_code(self):
        text = (ROOT / "scripts/find.py").read_text(encoding="utf-8")
        self.assertNotIn("tz, pozh, obshchie", text)

    def test_kinds_has_no_duplicates(self):
        self.assertEqual(len(validate.KINDS), len(set(validate.KINDS)))
        text = (ROOT / "scripts/validate.py").read_text(encoding="utf-8")
        line = next(line for line in text.splitlines() if line.startswith("KINDS = "))
        entries = line.split('"')[1::2]
        self.assertEqual(len(entries), len(set(entries)), f"KINDS содержит дубликаты: {line}")


if __name__ == "__main__":
    unittest.main()
