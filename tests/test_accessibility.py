import unittest

from cra.accessibility import helper_binary_path, helper_source_path


class AccessibilityTests(unittest.TestCase):
    def test_helper_source_path_points_to_repo_script(self) -> None:
        self.assertTrue(str(helper_source_path()).endswith("scripts/enable_ax_manual_accessibility.m"))

    def test_helper_binary_path_points_to_repo_var_bin(self) -> None:
        self.assertTrue(str(helper_binary_path()).endswith("var/bin/enable_ax_manual_accessibility"))


if __name__ == "__main__":
    unittest.main()
