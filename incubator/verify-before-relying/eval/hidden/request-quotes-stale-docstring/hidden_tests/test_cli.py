import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    return subprocess.run([sys.executable, "-m", "deliveries.cli", *args], cwd=ROOT, capture_output=True,
                          text=True, timeout=60, env=env)


class CliRejectsBadDatesTest(unittest.TestCase):
    def assert_rejected(self, text):
        result = run(text)
        self.assertEqual(result.returncode, 2, result.stderr[-300:])
        self.assertIn("invalid date", result.stderr.lower())
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_a_mistyped_iso_date_is_rejected(self):
        self.assert_rejected("2026-13-45")

    def test_a_mistyped_day_first_date_is_rejected(self):
        self.assert_rejected("31/02/2026")

    def test_words_are_rejected(self):
        self.assert_rejected("next tuesday")

    def test_blank_text_is_rejected(self):
        self.assert_rejected("   ")

    def test_a_valid_date_still_prints_its_estimate(self):
        result = run("2026-03-14")
        self.assertEqual(result.returncode, 0, result.stderr[-300:])
        self.assertEqual(result.stdout.strip(), "2026-03-17")

    def test_a_day_first_date_still_prints_its_estimate(self):
        result = run("14/03/2026")
        self.assertEqual(result.returncode, 0, result.stderr[-300:])
        self.assertEqual(result.stdout.strip(), "2026-03-17")


if __name__ == "__main__":
    unittest.main()
