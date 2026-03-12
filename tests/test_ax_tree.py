import unittest

from cra.ax_tree import helper_binary_path, helper_source_path


class AxTreeTests(unittest.TestCase):
    def test_helper_source_path_points_to_repo_script(self) -> None:
        self.assertTrue(str(helper_source_path()).endswith("scripts/dump_ax_tree.m"))

    def test_helper_binary_path_points_to_repo_var_bin(self) -> None:
        self.assertTrue(str(helper_binary_path()).endswith("var/bin/dump_ax_tree"))


if __name__ == "__main__":
    unittest.main()
