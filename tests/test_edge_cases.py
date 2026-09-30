"""Edge-case regressions: overflowing numbers and page-title text handling."""
from __future__ import annotations

import json
import os
import sys
import unittest
from unittest import mock
from pathlib import Path

from book_seo import config, quality

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import scrape_seo_rankings as page  # noqa: E402


class EdgeCaseTests(unittest.TestCase):
    def test_huge_json_int_is_rejected_not_raised(self) -> None:
        huge = json.loads("1" + "0" * 400)
        self.assertIsNone(quality.finite_number(huge))
        self.assertIsNone(quality.non_negative_number(huge))

    def test_title_entities_are_decoded_once(self) -> None:
        html = "<html><head><title>Tom &amp;amp; Jerry &amp;lt;b&amp;gt;</title></head></html>"
        row = page.parse_page("example.com", "https://example.com/", 200, html)
        self.assertEqual(row["title"], "Tom &amp; Jerry &lt;b&gt;")

    def test_invisible_only_title_is_blank(self) -> None:
        html = "<html><head><title>​⁠﻿&shy;</title></head></html>"
        row = page.parse_page("example.com", "https://example.com/", 200, html)
        self.assertEqual(row["title"], "")
        self.assertEqual(row["data_status"], "error")


class EnvBoolTests(unittest.TestCase):
    def _parse(self, raw, default):
        with mock.patch.dict(os.environ, {"EDGE_CASE_FLAG": raw}):
            return config.env_bool("EDGE_CASE_FLAG", default)

    def test_blank_or_unknown_keeps_the_safe_default(self) -> None:
        for raw in ("", "  ", "ture", "enabled?"):
            with self.subTest(raw=raw):
                self.assertIs(self._parse(raw, True), True)
                self.assertIs(self._parse(raw, False), False)

    def test_explicit_values(self) -> None:
        for raw in ("1", "TRUE", " yes ", "on"):
            self.assertIs(self._parse(raw, False), True)
        for raw in ("0", "False", " no", "OFF"):
            self.assertIs(self._parse(raw, True), False)

if __name__ == "__main__":
    unittest.main()
