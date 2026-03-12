import unittest

from cra.actuator import run_local_actuation


class ActuatorTests(unittest.TestCase):
    def test_run_local_actuation_dry_run_does_not_require_selector_config(self) -> None:
        result = run_local_actuation(
            "approve",
            "11111111-1111-4111-8111-111111111111",
            allow_live=False,
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(result["decision"], "approve")


if __name__ == "__main__":
    unittest.main()
