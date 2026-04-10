"""Tests for RustChain Bounty Hunter Agent."""

import unittest
import tempfile
import os

from config import Config
from scanner import Scanner
from evaluator import Evaluator
from tracker import Tracker
from submitter import Submitter


class TestConfig(unittest.TestCase):
    def test_defaults(self):
        cfg = Config()
        self.assertEqual(cfg.wallet, "zhaog100")
        self.assertEqual(cfg.min_score, 50.0)


class TestEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = Evaluator(Config())

    def test_extract_rtc_amount(self):
        issue = {"title": "[BOUNTY: 50 RTC] Some task", "body": ""}
        amount = self.evaluator._extract_amount(issue)
        self.assertEqual(amount, 50)

    def test_extract_usd_amount(self):
        issue = {"title": "Bounty $200", "body": ""}
        amount = self.evaluator._extract_amount(issue)
        self.assertEqual(amount, 2000)  # $200 / $0.10

    def test_evaluate_high_value(self):
        issue = {"title": "[BOUNTY: 100 RTC] Build Agent", "body": "build autonomous agent framework"}
        score = self.evaluator.evaluate(issue)
        self.assertGreater(score["total"], 50)
        self.assertEqual(score["verdict"], "CLAIM")

    def test_evaluate_low_value(self):
        issue = {"title": "Small fix", "body": "Fix a typo"}
        score = self.evaluator.evaluate(issue)
        self.assertEqual(score["verdict"], "SKIP")

    def test_complexity_easy(self):
        issue = {"title": "Write article", "body": ""}
        self.assertEqual(self.evaluator._estimate_complexity(issue), "easy")

    def test_complexity_hard(self):
        issue = {"title": "Autonomous AI agent framework", "body": ""}
        self.assertEqual(self.evaluator._estimate_complexity(issue), "hard")


class TestTracker(unittest.TestCase):
    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmpfile.close()
        self.tracker = Tracker(Config(), db_path=self.tmpfile.name)

    def tearDown(self):
        os.unlink(self.tmpfile.name)

    def test_add_and_get_task(self):
        issue = {"number": 123, "title": "Test bounty"}
        score = {"total": 75.0, "amount": 50}
        self.tracker.add_task(issue, score)
        tasks = self.tracker.get_pending_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["issue_number"], 123)

    def test_update_status(self):
        issue = {"number": 456, "title": "Test"}
        score = {"total": 80, "amount": 100}
        self.tracker.add_task(issue, score)
        self.tracker.update_status(456, "submitted", pr_url="https://github.com/pull/1")
        stats = self.tracker.get_stats()
        self.assertEqual(stats["submitted"], 1)

    def test_stats(self):
        stats = self.tracker.get_stats()
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["earnings_rtc"], 0)


class TestSubmitter(unittest.TestCase):
    def test_quality_check_clean(self):
        submitter = Submitter(Config())
        with tempfile.TemporaryDirectory() as td:
            # Create a clean file to check
            clean_file = os.path.join(td, "clean.py")
            with open(clean_file, "w") as f:
                f.write("print('hello')\n")
            ok, issues = submitter.quality_check(clean_file)
            self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
