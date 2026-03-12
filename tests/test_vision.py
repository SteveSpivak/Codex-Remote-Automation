import unittest

from cra.vision import (
    click_helper_binary_path,
    click_helper_source_path,
    find_text_target,
    normalize_ocr_text,
    ocr_helper_binary_path,
    ocr_helper_source_path,
)


class VisionTests(unittest.TestCase):
    def test_helper_paths_point_to_repo_files(self) -> None:
        self.assertTrue(str(ocr_helper_source_path()).endswith("scripts/capture_codex_window_ocr.m"))
        self.assertTrue(str(ocr_helper_binary_path()).endswith("var/bin/capture_codex_window_ocr"))
        self.assertTrue(str(click_helper_source_path()).endswith("scripts/click_screen_point.m"))
        self.assertTrue(str(click_helper_binary_path()).endswith("var/bin/click_screen_point"))

    def test_normalize_ocr_text_collapses_whitespace(self) -> None:
        self.assertEqual(normalize_ocr_text("  Tool   approval "), "tool approval")

    def test_find_text_target_requires_context_and_prefers_exact_match(self) -> None:
        payload = {
            "text_items": [
                {"text": "Tool approval", "confidence": 0.99},
                {
                    "text": "Approve",
                    "confidence": 0.95,
                    "screen_center": {"x": 100.0, "y": 200.0},
                },
                {
                    "text": "Approve request",
                    "confidence": 0.99,
                    "screen_center": {"x": 150.0, "y": 250.0},
                },
            ]
        }

        target = find_text_target(
            payload,
            text_candidates=["Approve"],
            required_context_phrases=["Tool approval"],
        )

        self.assertIsNotNone(target)
        self.assertEqual(target["text"], "Approve")

    def test_find_text_target_returns_none_when_context_missing(self) -> None:
        payload = {
            "text_items": [
                {"text": "Approve", "confidence": 0.95},
            ]
        }

        target = find_text_target(
            payload,
            text_candidates=["Approve"],
            required_context_phrases=["Tool approval"],
        )

        self.assertIsNone(target)


if __name__ == "__main__":
    unittest.main()
