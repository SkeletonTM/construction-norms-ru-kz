#!/usr/bin/env python3
"""Tests for link-check classification."""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate  # noqa: E402


class LinkCheck(unittest.TestCase):
    def test_dead_link_is_error(self):
        for code in (404, 410):
            with self.subTest(code=code):
                self.assertEqual(validate.link_verdict("https://example.org/x", code), "error")

    def test_blocked_link_is_warning(self):
        cases = [("https://example.org/x", code) for code in (None, 403, 429, 503)]
        cases.append(("https://[malformed", 200))  # urlparse raises ValueError
        cases.append((123, 200))  # non-string URL must not crash
        for url, code in cases:
            with self.subTest(url=url, code=code):
                self.assertEqual(validate.link_verdict(url, code), "warning")

    def test_bot_walled_host_is_always_warning(self):
        self.assertEqual(validate.link_verdict("https://docs.cntd.ru/document/1", 200), "warning")
        self.assertEqual(validate.link_verdict("https://docs.cntd.ru./document/1", 404), "warning")

    def test_healthy_link_is_ok(self):
        self.assertEqual(validate.link_verdict("https://prg.kz/document/?doc_id=1", 200), "ok")

    def test_check_links_skips_soft_host_once_and_keeps_dead_error(self):
        cards = {"a": {"_path": Path("catalog/ru/a.yaml"), "sources": [
            {"url": "https://docs.cntd.ru/document/1"},
            {"url": "https://docs.cntd.ru/document/1"},
            {"url": "https://example.org/dead"},
        ]}}
        with patch.object(validate, "probe", return_value=404) as probe:
            errs, skipped, probed = validate.check_links(cards)
        self.assertEqual((skipped, probed), (1, 1))
        self.assertEqual(len(errs), 1)
        self.assertEqual(probe.call_count, 1)

    def test_check_links_treats_server_error_as_warning(self):
        cards = {"a": {"_path": Path("catalog/ru/a.yaml"), "sources": [{"url": "https://example.org/down"}]}}
        with patch.object(validate, "probe", return_value=503):
            errs, skipped, probed = validate.check_links(cards)
        self.assertEqual((len(errs), skipped, probed), (0, 0, 1))

        # A non-string URL must be reported as an error, not crash the checker.
        cards = {"a": {"_path": Path("catalog/ru/a.yaml"), "sources": [{"url": 123}]}}
        with patch.object(validate, "probe", return_value=200) as probe:
            errs, skipped, probed = validate.check_links(cards)
        self.assertEqual((len(errs), skipped, probed), (1, 0, 0))
        self.assertIn("123", errs[0])
        probe.assert_not_called()

    def test_check_links_deduplicates_non_soft_urls(self):
        cards = {"a": {"_path": Path("catalog/ru/a.yaml"), "sources": [
            {"url": "https://example.org/same"},
            {"url": "https://example.org/same"},
        ]}}
        with patch.object(validate, "probe", return_value=200) as probe:
            errs, skipped, probed = validate.check_links(cards)
        self.assertEqual((len(errs), skipped, probed), (0, 0, 1))
        self.assertEqual(probe.call_count, 1)

    def test_main_reports_skipped_links_and_strict_exit(self):
        cards = {"a": {"_path": Path("catalog/ru/a.yaml"), "status": "действует"}}
        with patch.object(validate, "load_cards", return_value=(cards, [])), \
             patch.object(validate, "check_card", return_value=([], [])), \
             patch.object(validate, "check_links", return_value=([], 1, 40)), \
             patch.object(sys, "argv", ["validate.py", "--links"]), \
             redirect_stdout(io.StringIO()) as out:
            rc = validate.main()
        text = out.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn("пропущена 1 ссылка", text)
        self.assertIn("проверено ссылок: 40", text)
        self.assertIn("ошибок: 0", text)
        with patch.object(validate, "load_cards", return_value=(cards, [])), \
             patch.object(validate, "check_card", return_value=([], [])), \
             patch.object(validate, "check_links", return_value=([], 1, 40)), \
             patch.object(sys, "argv", ["validate.py", "--links", "--strict"]), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(validate.main(), 1)


if __name__ == "__main__":
    unittest.main()
