"""Stdlib unittest tests for envdrift. No external deps."""
import json
import sys
import unittest
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import envdrift  # noqa: E402


class TestParseEnv(unittest.TestCase):
    def test_parse_basic(self):
        p = ROOT / "tests" / "_a.env"
        p.write_text("FOO=1\nBAR='two'\n# comment\nexport BAZ=\"three\"\n")
        keys, dupes = envdrift.parse_env(p)
        self.assertEqual(keys, {"FOO": "1", "BAR": "two", "BAZ": "three"})
        self.assertEqual(dupes, [])
        p.unlink()

    def test_parse_dupes(self):
        p = ROOT / "tests" / "_b.env"
        p.write_text("X=1\nX=2\nY=3\n")
        keys, dupes = envdrift.parse_env(p)
        self.assertEqual(keys["X"], "2")
        self.assertEqual(dupes, ["X"])
        p.unlink()


class TestAnalyze(unittest.TestCase):
    def test_drift_detected(self):
        a = ROOT / "tests" / "_x.env"
        b = ROOT / "tests" / "_y.env"
        a.write_text("A=1\nB=2\n")
        b.write_text("A=1\n")
        report = envdrift.analyze([a, b], strict=False)
        self.assertTrue(report["drift"])
        self.assertIn("B", report["results"][1]["missing"])
        a.unlink(); b.unlink()

    def test_no_drift(self):
        a = ROOT / "tests" / "_x.env"
        b = ROOT / "tests" / "_y.env"
        a.write_text("A=1\nB=2\n")
        b.write_text("A=v\nB=v\n")
        report = envdrift.analyze([a, b], strict=False)
        self.assertFalse(report["drift"])
        a.unlink(); b.unlink()

    def test_strict_placeholders(self):
        a = ROOT / "tests" / "_x.env"
        b = ROOT / "tests" / "_y.env"
        a.write_text("DB=postgres\n")
        b.write_text("DB=changeme\n")
        report = envdrift.analyze([a, b], strict=True)
        self.assertTrue(report["drift"])
        self.assertIn("DB", report["results"][1]["placeholders"])
        a.unlink(); b.unlink()


class TestCli(unittest.TestCase):
    def test_json_output(self):
        a = ROOT / "tests" / "_x.env"
        b = ROOT / "tests" / "_y.env"
        a.write_text("A=1\nB=2\n")
        b.write_text("A=1\n")
        old = sys.stdout
        sys.stdout = StringIO()
        try:
            rc = envdrift.main([str(a), str(b), "--json"])
            out = sys.stdout.getvalue()
        finally:
            sys.stdout = old
        self.assertEqual(rc, 1)
        data = json.loads(out)
        self.assertTrue(data["drift"])
        a.unlink(); b.unlink()

    def test_needs_two_files(self):
        old = sys.stderr
        sys.stderr = StringIO()
        try:
            rc = envdrift.main([str(ROOT / "envdrift.py")])
        finally:
            sys.stderr = old
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
