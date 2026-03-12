import unittest

from cra.ui_probe import parse_probe_output


class UiProbeTests(unittest.TestCase):
    def test_parse_probe_output_extracts_buttons(self) -> None:
        raw_output = "\n".join(
            [
                "PROCESS\tCodex",
                "WINDOW\tTool approval",
                "ELEMENT\tname=\tax_description=Approve\trole_description=button",
                "BUTTON\tname=\tax_description=Approve\trole_description=button\thelp=",
                "BUTTON\tname=\tax_description=Deny\trole_description=button\thelp=",
            ]
        )

        parsed = parse_probe_output(raw_output)
        self.assertEqual(parsed["process"], "Codex")
        self.assertEqual(parsed["window"], "Tool approval")
        self.assertEqual(parsed["elements"][0]["role_description"], "button")
        self.assertEqual(len(parsed["buttons"]), 2)
        self.assertEqual(parsed["buttons"][0]["ax_description"], "Approve")


if __name__ == "__main__":
    unittest.main()
