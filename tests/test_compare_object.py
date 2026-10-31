# SPDX-License-Identifier: MulanPSL-2.0

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


COMPARE = Path(__file__).resolve().parents[1] / "maple_test" / "compare.py"


class CompareObjectTest(unittest.TestCase):
    def test_file_and_stdin_inputs(self):
        with tempfile.TemporaryDirectory(prefix="compare input ") as temp_dir:
            root = Path(temp_dir)
            rules = root / "rules.cj"
            output = root / "actual output.txt"
            rules.write_text("// ASSERT: scan 你好\n", encoding="utf-8")
            output.write_text("你好\n", encoding="utf-8")
            command = [sys.executable, str(COMPARE), "--comment", "//", str(rules)]
            env = dict(os.environ, PYTHONIOENCODING="utf-8")
            cases = [
                ("default stdin", [], "你好\n", 0, "[Compare Pass]"),
                ("explicit file", ["--compare_object", str(output)], "", 0, "[Compare Pass]"),
                ("option without value", ["--compare_object"], "你好\n", 0, "[Compare Pass]"),
                ("stdin dash", ["--compare_object", "-"], "你好\n", 0, "[Compare Pass]"),
                ("stdin mismatch", [], "wrong\n", 1, "[Compare Fail]"),
                ("missing file", ["--compare_object", str(root / "missing.txt")], "", 2, "error:"),
            ]
            for name, options, content, expected_code, marker in cases:
                with self.subTest(name=name):
                    result = subprocess.run(
                        command + options, input=content, capture_output=True,
                        text=True, encoding="utf-8", env=env, timeout=10,
                    )
                    combined = result.stdout + result.stderr
                    self.assertEqual(result.returncode, expected_code, combined)
                    self.assertIn(marker, combined)
                    self.assertNotIn("Traceback", combined)

            output.write_text("wrong\n", encoding="utf-8")
            result = subprocess.run(
                command + ["--compare_object", str(output)], input="你好\n",
                capture_output=True, text=True, encoding="utf-8", env=env, timeout=10,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("[Compare Fail]", result.stdout)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
