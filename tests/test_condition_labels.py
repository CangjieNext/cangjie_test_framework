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
from pathlib import Path


MAPLE_TEST_DIR = Path(__file__).resolve().parent.parent / "maple_test"
sys.path.insert(0, str(MAPLE_TEST_DIR))

from utils import filter_command_line, filter_line, process_condition


class ConditionLabelTest(unittest.TestCase):
    def test_process_condition_supports_underscore_label(self):
        conditions = {"target_linux", "debug_mode"}

        self.assertTrue(process_condition("(target_linux)", conditions))
        self.assertTrue(process_condition("(target_linux&debug_mode)", conditions))
        self.assertFalse(process_condition("(target_windows|debug_mode_off)", conditions))

    def test_filter_line_supports_underscore_label(self):
        conditions = {"target_linux"}
        line = "(target_linux) ASSERT: expected output"

        self.assertEqual("expected output", filter_line(line, "ASSERT", conditions))

    def test_filter_command_line_supports_underscore_label(self):
        conditions = {"target_linux"}
        line = "(target_linux) EXEC: %compiler %f -o %output"

        command = filter_command_line(line, conditions, run_script=None, compatible=False)

        self.assertEqual("%compiler %f -o %output", command["cmd"])
        self.assertEqual(0, command["exit_code"])
        self.assertFalse(command["PIPE"])


if __name__ == "__main__":
    unittest.main()
