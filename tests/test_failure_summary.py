#!/usr/bin/python3
# -*- coding:utf-8 -*-
#
# Copyright (c) [2020] Huawei Technologies Co.,Ltd.All rights reserved.
#
# OpenArkCompiler is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#
#     http://license.coscl.org.cn/MulanPSL2
#
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR
# FITNESS FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
#
import sys
import unittest
from collections import defaultdict
from pathlib import Path


MAPLE_TEST_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MAPLE_TEST_DIR))

from maple_test.task import TestSuiteTask
from maple_test.utils import FAIL, NOT_RUN, PASS, UNRESOLVED


class FakeTask:
    def __init__(self):
        self.name = "fake_task"
        self.result = (FAIL, None)
        self.case_path = Path("compiler/cjnative/foo/bar_01.cj")
        self.temp_dir = "bar_01_c0ffee"
        self.log_config = "HLT/compiler/cjnative/foo/bar_01_c0ffee"


class FailureSummaryTest(unittest.TestCase):
    def test_failed_case_summary_uses_log_config_path(self):
        suite = TestSuiteTask.__new__(TestSuiteTask)
        failed_task = FakeTask()
        suite.name = "x86_64-unknown-linux-gnu"
        suite.path = Path("testsuites/HLT")
        suite.task_set = {"basic_cfg": [failed_task]}
        suite.task_set_result = {
            "basic_cfg": defaultdict(
                int, {FAIL: 1, PASS: 0, NOT_RUN: 0, UNRESOLVED: 0}
            )
        }
        suite.result = defaultdict(int)

        summary = suite.gen_summary(print_type=[FAIL])

        self.assertIn(
            "Case: {}".format(Path("compiler/cjnative/foo/bar_01.cj")), summary
        )
        self.assertIn(
            "LogFile: HLT/compiler/cjnative/foo/bar_01_c0ffee.log", summary
        )
        self.assertNotIn("LogFile: bar_01_c0ffee.log", summary)


if __name__ == "__main__":
    unittest.main()
