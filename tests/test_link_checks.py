#!/usr/bin/env python3
"""Tests for link-check classification."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate  # noqa: E402


class LinkCheck(unittest.TestCase):
    def test_dead_link_is_error(self):
        for code in (404, 410):
            with self.subTest(code=code):
                self.assertEqual(validate.link_verdict("https://example.org/x", code), "error")

    def test_blocked_link_is_warning(self):
        for code in (None, 403, 429, 503):
            with self.subTest(code=code):
                self.assertEqual(validate.link_verdict("https://example.org/x", code), "warning")

    def test_bot_walled_host_is_always_warning(self):
        self.assertEqual(validate.link_verdict("https://docs.cntd.ru/document/1", 200), "warning")

    def test_healthy_link_is_ok(self):
        self.assertEqual(validate.link_verdict("https://prg.kz/document/?doc_id=1", 200), "ok")


if __name__ == "__main__":
    unittest.main()
