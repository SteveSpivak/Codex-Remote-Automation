import unittest

from cra.discovery import summarize_breadcrumbs


class DiscoveryTests(unittest.TestCase):
    def test_summarize_breadcrumbs_extracts_ui_and_http_hints(self) -> None:
        payload = {
            "scope": {
                "breadcrumbs": [
                    {"category": "ui.click", "message": "button[aria-label=\"Approve\"]"},
                    {"category": "ui.click", "message": "button[aria-label=\"Approve\"]"},
                    {
                        "category": "electron.net",
                        "data": {"url": "https://chatgpt.com/backend-api/wham/tasks/list"},
                    },
                ]
            }
        }

        summary = summarize_breadcrumbs(payload)
        self.assertEqual(summary["ui_messages"], ['button[aria-label="Approve"]'])
        self.assertEqual(summary["http_urls"], ["https://chatgpt.com/backend-api/wham/tasks/list"])
        self.assertIn("ui.click", summary["categories"])


if __name__ == "__main__":
    unittest.main()
