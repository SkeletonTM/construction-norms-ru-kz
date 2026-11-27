#!/usr/bin/env python3
"""Regression tests for status and identity matching in check_status.py."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_status  # noqa: E402


class StatusChecks(unittest.TestCase):
    def test_row_matches_accepts_exact_kind_and_number(self):
        card = {"kind": "ГОСТ", "number": "2405-88"}
        row = {"doc": "ГОСТ 2405-88", "date": "01.01.1988", "status": "действует"}
        self.assertTrue(check_status.row_matches(card, row))

    def test_row_matches_rejects_different_kind_prefix(self):
        card = {"kind": "ГОСТ", "number": "2405-88"}
        row = {"doc": "ГОСТ Р 2405-88", "date": "01.01.1988", "status": "действует"}
        self.assertFalse(check_status.row_matches(card, row))

    def test_row_matches_rejects_longer_number(self):
        card = {"kind": "ГОСТ", "number": "2405-88"}
        row = {"doc": "ГОСТ 2405-880", "date": "01.01.1988", "status": "действует"}
        self.assertFalse(check_status.row_matches(card, row))

    def test_row_matches_accepts_title_after_number(self):
        card = {"kind": "ГОСТ", "number": "2405-88"}
        row = {"doc": "ГОСТ 2405-88 Приборы измерительные", "date": "01.01.1988", "status": "действует"}
        self.assertTrue(check_status.row_matches(card, row))

    def test_row_matches_accepts_parentheses_and_en_dash(self):
        card = {"kind": "ГОСТ", "number": "2405-88"}
        row = {"doc": "ГОСТ 2405–88 (Приборы измерительные)", "date": "01.01.1988", "status": "действует"}
        self.assertTrue(check_status.row_matches(card, row))

    def test_row_matches_accepts_gost_r_with_title(self):
        card = {"kind": "ГОСТ Р", "number": "2405-88"}
        row = {"doc": "ГОСТ Р 2405-88 Приборы", "date": "01.01.1988", "status": "действует"}
        self.assertTrue(check_status.row_matches(card, row))

    def test_acceptance_is_not_an_active_status(self):
        self.assertNotEqual(check_status.STATUS_WORDS.get("принят"), "действует")

    def test_prg_status_keeps_the_whole_phrase(self):
        page = (
            "<div>Информация о документе</div>"
            "<span>Статус:</span><span>Не действует</span>"
            "<span>Дата последнего изменения:</span>"
        )
        original = check_status.fetch
        check_status.fetch = lambda url, data=None, timeout=30: page
        try:
            info = check_status.prg_status(1)
        finally:
            check_status.fetch = original
        self.assertEqual(info["status"], "Не действует")


if __name__ == "__main__":
    unittest.main()
