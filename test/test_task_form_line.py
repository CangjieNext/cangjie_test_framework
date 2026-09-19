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
"""Unit tests for SingleTask._form_line placeholder substitution.

Covers cangjie_test_framework issue #59: when one config key is a prefix
of another (e.g. 'dump-ir' vs 'dump-ir-to-screen'), the longer key must
win the substitution.  Also guards the pre-existing word-boundary rules
(alphanumeric and '_' must not terminate a key) and the multi-pass
resolution of nested '%other' references.

Run from the repo root:

    python test/test_task_form_line.py

The file is run directly (not via ``python -m unittest test.``) because a
plain ``test`` package on sys.path shadows the stdlib ``test`` package,
which breaks module resolution for ``python -m`` imports.
"""
import logging
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from maple_test import configs
from maple_test.task import SingleTask

if configs.LOGGER is None:
    configs.LOGGER = logging.getLogger("test_task_form_line")


class TestFormLine(unittest.TestCase):
    """Substitution semantics of SingleTask._form_line (static method)."""

    CFG = {
        "internal_var": {
            # issue #59 pair: short key is a prefix of the long key.
            "dump-ir": "--dump-ir",
            "dump-ir-to-screen": "--dump-ir --dump-to-screen",
            "n": "abc",
            "suffix": "exe",
            "compiler": "cjc",
            "compiler_extra": "--extra",
        }
    }

    def substitute(self, line, cfg=None):
        return SingleTask._form_line(line, cfg or self.CFG)

    def test_long_key_wins_over_prefix(self):
        # Core case of issue #59: before the fix the short key
        # 'dump-ir' raced first and '%dump-ir-to-screen' was rewritten
        # into the non-existent option '--dump-ir-to-screen'.
        self.assertEqual(
            self.substitute("cj_test %dump-ir-to-screen -o %n.exe"),
            "cj_test --dump-ir --dump-to-screen -o abc.exe",
        )

    def test_short_key_still_replaced(self):
        self.assertEqual(
            self.substitute("cj_test %dump-ir %n"),
            "cj_test --dump-ir abc",
        )

    def test_underscore_is_not_a_boundary(self):
        # Pre-existing rule: '%compiler' must not fire inside
        # '%compiler_extra' because '_' continues the key name.
        self.assertEqual(
            self.substitute("%compiler %compiler_extra"),
            "cjc --extra",
        )

    def test_alnum_is_not_a_boundary(self):
        self.assertEqual(
            self.substitute("%compiler2"),
            "%compiler2",  # '2' continues the key; no match
        )

    def test_key_at_word_start(self):
        self.assertEqual(self.substitute("--opt %compiler"), "--opt cjc")

    def test_key_at_end_of_line(self):
        self.assertEqual(self.substitute("use %n"), "use abc")

    def test_no_placeholders_unchanged(self):
        self.assertEqual(self.substitute("nothing here"), "nothing here")

    def test_value_embedded_in_string(self):
        self.assertEqual(self.substitute("output=%n.%suffix"), "output=abc.exe")

    def test_nested_reference_resolved_in_multi_pass(self):
        # 'output' value references %n and %suffix defined elsewhere;
        # resolution must be order-independent (multi-pass fixpoint).
        cfg = {
            "internal_var": {
                "output": "%n.%suffix",
                "suffix": "exe",
                "n": "case1",
            }
        }
        self.assertEqual(
            SingleTask._form_line("artifact=%output", cfg),
            "artifact=case1.exe",
        )

    def test_circular_reference_does_not_hang(self):
        # Guard: circular refs must terminate via the 20-iteration cap
        # (warning is logged through configs.LOGGER) and return the
        # unresolved placeholder instead of looping forever.
        cfg = {
            "internal_var": {
                "a": "%b",
                "b": "%a",
            }
        }
        self.assertEqual(
            SingleTask._form_line("x=%a", cfg),
            "x=%a",
        )

    def test_issue59_regression_both_keys_coexist(self):
        # Both keys of the prefix pair may appear on one line; each must
        # resolve to its own value.
        self.assertEqual(
            self.substitute("%dump-ir %dump-ir-to-screen"),
            "--dump-ir --dump-ir --dump-to-screen",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
