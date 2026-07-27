"""Unit tests for Questioner optimizations."""

from __future__ import annotations

import unittest
import sys
from pathlib import Path

# Setup path so tests can run against local package
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from questioner.stats import fullwidth_char_count, validate_nickname
from questioner.llm import _extract_json_blob, _parse_json_text


class TestQuestionerOptimizations(unittest.TestCase):
    def test_fullwidth_char_count(self) -> None:
        # English letters should be 0.5 units each
        self.assertEqual(fullwidth_char_count("abc"), 1.5)
        # Chinese characters should be 1.0 unit each
        self.assertEqual(fullwidth_char_count("你好世界"), 4.0)
        # Mixed full-width and half-width characters
        # "Hello " is 6 halfwidth (3.0) + "世界" (2.0) = 5.0 units
        self.assertEqual(fullwidth_char_count("Hello 世界"), 5.0)

    def test_validate_nickname(self) -> None:
        # Valid Chinese name (4 chars = 4.0 units <= 12)
        ok, msg = validate_nickname("科学研究者")
        self.assertTrue(ok, f"Expected valid: {msg}")

        # Valid English name (20 half-width chars = 10.0 units <= 12)
        ok, msg = validate_nickname("Johnathan Smith Jr.")
        self.assertTrue(ok, f"Expected valid: {msg}")

        # Too long Chinese name (13 chars = 13.0 units > 12)
        ok, msg = validate_nickname("这是一个非常非常非常非常非常长名字")
        self.assertFalse(ok)
        self.assertIn("at most 12 full-width characters", msg)

        # Too long English name (26 half-width chars = 13.0 units > 12)
        ok, msg = validate_nickname("abcdefghijklmnopqrstuvwxyz")
        self.assertFalse(ok)
        self.assertIn("at most 12 full-width characters", msg)

    def test_extract_json_blob_robustness(self) -> None:
        # Test standard JSON object extraction
        self.assertEqual(_extract_json_blob("some text\n```json\n{\"a\": 1}\n```\nother"), "{\"a\": 1}")
        self.assertEqual(_extract_json_blob("some text\n{\"a\": 1}\nother"), "{\"a\": 1}")

        # Test JSON array extraction (our optimization!)
        self.assertEqual(_extract_json_blob("some text\n```json\n[1, 2, 3]\n```\nother"), "[1, 2, 3]")
        self.assertEqual(_extract_json_blob("some text\n[1, 2, 3]\nother"), "[1, 2, 3]")

    def test_parse_json_text(self) -> None:
        # Parse parsed dict
        self.assertEqual(_parse_json_text("```json\n{\"a\": 1}\n```"), {"a": 1})
        # Parse parsed list
        self.assertEqual(_parse_json_text("```\n[1, 2, 3]\n```"), [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
