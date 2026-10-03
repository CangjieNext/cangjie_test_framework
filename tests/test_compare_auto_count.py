# Copyright (c) 2026 赵家耀. All rights reserved.
#
# Licensed under Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#     http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""Regression coverage for exact occurrence counts with regex-auto.

Run from the repository root: python3 -m unittest discover -s tests -v
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


COMPARE = Path(__file__).resolve().parents[1] / "maple_test" / "compare.py"


class AutoCountCLITest(unittest.TestCase):
    def assert_compare(self, flag, pattern, output, expected_code):
        with tempfile.TemporaryDirectory() as directory:
            case = Path(directory) / "case.cj"
            case.write_text(f"// ASSERT: {flag} {pattern}\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(COMPARE), "--comment", "//", str(case)],
                input=output, text=True, capture_output=True, check=False,
            )
        self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)

    def test_exact_two_rejects_zero(self):
        self.assert_compare("regex-auto-2", "foo bar", "unrelated\n", 1)

    def test_exact_two_rejects_one(self):
        self.assert_compare("regex-auto-2", "foo bar", "foo bar\n", 1)

    def test_exact_two_accepts_two(self):
        self.assert_compare("regex-auto-2", "foo bar", "foo bar\nfoo bar\n", 0)

    def test_exact_two_rejects_three(self):
        self.assert_compare("regex-auto-2", "foo bar", "foo bar\n" * 3, 1)

    def test_zero_accepts_absent_pattern(self):
        self.assert_compare("regex-auto-0", "foo bar", "unrelated\n", 0)

    def test_zero_rejects_present_pattern(self):
        self.assert_compare("regex-auto-0", "foo bar", "foo bar\n", 1)

    def test_count_survives_reverse_keyword_order(self):
        self.assert_compare("regex-2-auto", "foo bar", "foo bar\n", 1)

    def test_variable_whitespace_is_still_accepted(self):
        self.assert_compare("regex-auto-2", "foo bar", "foo\tbar\nfoo   bar\n", 0)

    def test_regex_metacharacters_remain_literal(self):
        self.assert_compare("regex-auto-2", "a.b [x]", "axb [x]\na.b\t[x]\n", 1)

    def test_literal_metacharacters_exact_two(self):
        self.assert_compare("regex-auto-2", "a.b [x]", "a.b [x]\na.b\t[x]\n", 0)

    def test_without_count_still_accepts_any_match(self):
        self.assert_compare("regex-auto", "foo bar", "foo bar\n" * 3, 0)

    def test_without_count_still_rejects_no_match(self):
        self.assert_compare("regex-auto", "foo bar", "unrelated\n", 1)


if __name__ == "__main__":
    unittest.main()
