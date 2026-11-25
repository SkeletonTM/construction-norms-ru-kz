#!/usr/bin/env python3
"""Keep documentation in sync with validation constants."""
import ast
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate  # noqa: E402


def kinds_literal_values():
    tree = ast.parse((ROOT / "scripts/validate.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "KINDS" for t in node.targets
        ):
            return [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
    raise AssertionError("KINDS assignment not found")


def scope_help_string():
    tree = ast.parse((ROOT / "scripts/find.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            if not any(isinstance(a, ast.Constant) and a.value == "--scope" for a in node.args):
                continue
            for kw in node.keywords:
                if kw.arg == "help" and isinstance(kw.value, ast.Constant):
                    return kw.value.value
    raise AssertionError("--scope help not found")


class DocsConsistency(unittest.TestCase):
    def test_schema_scope_table_matches_validator(self):
        text = (ROOT / "_schema.md").read_text(encoding="utf-8")
        section = text.split("### Разделы (`scope`)", 1)[1].split("\n## ", 1)[0]
        codes = set(re.findall(r"^\| `([a-z]+)` \|", section, re.M))
        self.assertEqual(
            codes, validate.SCOPES,
            f"таблица scope не совпадает с SCOPES: {sorted(codes ^ validate.SCOPES)}",
        )

    def test_find_scope_help_has_no_unknown_code(self):
        help_text = scope_help_string()
        tokens = set(re.findall(r"\b[a-z][a-z0-9]*\b", help_text))
        self.assertNotIn("tz", tokens, f"в --scope help есть неизвестный код: {help_text}")
        self.assertIn("_schema.md", help_text)
        self.assertTrue(tokens & validate.SCOPES, f"в --scope help нет примеров кодов: {help_text}")

    def test_kinds_literal_has_no_duplicates(self):
        values = kinds_literal_values()
        self.assertEqual(len(values), len(set(values)), f"KINDS содержит дубликаты: {values}")

    def test_schema_kind_list_matches_validator(self):
        text = (ROOT / "_schema.md").read_text(encoding="utf-8")
        row = next(line for line in text.splitlines() if line.startswith("| `kind` |"))
        documented = set(re.findall(r"`([^`]+)`", row)) - {"kind"}
        self.assertEqual(
            documented, set(validate.KINDS),
            f"список kind в _schema.md не совпадает с validate.KINDS: {sorted(documented ^ set(validate.KINDS))}",
        )


if __name__ == "__main__":
    unittest.main()
