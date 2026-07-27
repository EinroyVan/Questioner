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
from questioner.report_note import build_obsidian_literature_note
from questioner.schemas import (
    KnowledgeExtractionResult,
    LiteratureMetadata,
    LiteratureAnalysis,
    IntroductionSection,
    MethodsSection,
    ResultsSection,
    DiscussionSection,
)


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

    def test_build_obsidian_literature_note(self) -> None:
        # Mock knowledge extraction result
        metadata = LiteratureMetadata(
            title="A Novel Method for RNA Editing",
            journal="Nature Biotechnology",
            impact_factor="38.1",
            first_author="Alice Smith",
            first_author_affiliation="MIT",
            published_date="2026-05-12",
            doi="10.1038/nbt.1234",
            field_tags=["molecular biology", "RNA editing"]
        )
        analysis = LiteratureAnalysis(
            introduction=IntroductionSection(
                hook="RNA editing holds immense therapeutic potential.",
                research_gap="Current tools have high off-target rates.",
                proposed_approach="We develop a high-fidelity CAS enzyme."
            ),
            methods=MethodsSection(
                technical_innovation="Engineered CAS-HF enzyme.",
                benchmarks_evaluation="Compared against wildtype CAS in HeLa cells."
            ),
            results=ResultsSection(
                key_findings=["CAS-HF reduced off-targets by 98%.", "Maintained 90% editing efficiency."],
                evidence_quality="Verified with deep sequencing in triplicate."
            ),
            discussion=DiscussionSection(
                limitations="Delivery via AAV is still challenging.",
                future_directions="Develop nanoparticle delivery systems."
            )
        )
        knowledge = KnowledgeExtractionResult(
            source_text_preview="Excerpt...",
            literature_metadata=metadata,
            literature_analysis=analysis,
            entities=["CAS-HF", "HeLa cells"]
        )

        note = build_obsidian_literature_note(knowledge, category="方法学")

        # Assertions
        self.assertIn("category: 方法学", note)
        self.assertIn("journal: \"Nature Biotechnology\"", note)
        self.assertIn("first_author: \"Alice Smith\"", note)
        self.assertIn("published_date: 2026.05", note)  # Date parsing!
        self.assertIn("期刊：[[Nature Biotechnology]]", note)
        self.assertIn("作者：[[Alice Smith]]", note)
        self.assertIn("时间：[[2026.05]]", note)
        self.assertIn("- 背景（为什么要研究，跟之前的研究相比有什么创新点？）", note)
        self.assertIn("起因 (Hook)", note)
        self.assertIn("CAS-HF reduced off-targets by 98%.", note)
        self.assertIn("[[CAS-HF]] [[HeLa cells]]", note)  # Wikilinks at the bottom!


if __name__ == "__main__":
    unittest.main()
