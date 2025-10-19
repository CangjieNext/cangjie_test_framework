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
# FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
#
import platform
import shlex
import re
from functools import total_ordering

from maple_test.utils import PASS, EXEC_FLAG, SEPARATE_FILE_DIRECTIVE, ERRCHECK_FLAG, EXPECT_FLAG, DEPENDENCE_FLAG, TIMEOUT_FLAG, LEVEL_FLAG
from maple_test.utils import read_file, safe_print
from maple_test.utils import split_comment, filter_line, filter_command_line, precheck_flag, filter_level
from maple_test.utils import FAIL, UNRESOLVED
from maple_test import configs

is_initialized = False


def ensure_config_initialized():
    global is_initialized
    if not is_initialized:
        _, _, _ = configs.init_config()
        is_initialized = True


class Case:
    def __init__(self, path, test_path, comment, condition, run_script, level=None):
        if level is None:
            level = set()
        if path != test_path:
            self.name = str(path)
            self.path = test_path / path
            self.test_name = test_path.name
        else:
            self.name = str(path.name)
            self.path = path
            self.test_name = path.parent.name
        self.test_path = test_path
        self.relative_path = path
        self.comment = comment
        try:
            _, comment_lines = split_comment(comment, read_file(self.path), )
        except UnicodeDecodeError as e:
            safe_print('[WARNING] ignore {} for {}.'.format(self.name, e))
            self.commands = []
            self.expect = []
            self.dependence = {}
            self.timeout = 300
            self.level = False
        else:
            self.level = extract_level(comment_lines, level, condition)
            self.commands = enumerate_compares(extract_commands(comment_lines, condition, run_script))
            self.expect = extract_expect(comment_lines)
            self.dependence = extract_dependence(comment_lines, condition)
            self.separation_by_files = extract_separation_by_files(comment_lines, self.path, condition)
            self.timeout = extract_timeout(comment_lines, condition)
        if not self.level:
            self.relative_path = ''

    def __repr__(self):
        return str(self.relative_path)


def extract_expect(comment_lines):
    expect_line = [filter_line(line, EXPECT_FLAG) for line in comment_lines]
    expect_line = [line for line in expect_line if line]
    if not expect_line:
        return PASS
    return expect_line[-1]


def extract_dependence(comment_lines, condition):
    support_separartor = ",; "
    dependence = []
    for line in comment_lines:
        line = filter_line(line, DEPENDENCE_FLAG, condition)
        if not line:
            continue
        parser = shlex.shlex(line)
        parser.whitespace = parser.whitespace + support_separartor
        parser.whitespace_split = True
        dependence += list(parser)
    return set(dependence)


def extract_separation_by_files(comment_lines, filepath, condition):
    # Check if file need to be separated
    need_separation = False
    for line in comment_lines:
        if filter_line(line, SEPARATE_FILE_DIRECTIVE, condition):
            need_separation = True
            break
    
    if not need_separation:
        return []
    
    # Return pairs of (file_path, file_content)
    separation = []
    cur_file_lines = []
    cur_file_path = ""
    with open(filepath) as file:
        for line in file:
            match = re.match(r'//\s*' + SEPARATE_FILE_DIRECTIVE + '\s*:\s*(.+)\s*', line)

            if not match:
                cur_file_lines.append(line)
            else:
                # save previous file content
                if cur_file_path != "":
                    separation.append((cur_file_path, '\n'.join(cur_file_lines)))
                # set new separation buffer
                cur_file_lines = []
                cur_file_path = match.group(1).strip()
                if cur_file_path == "":
                    raise Exception('ERROR: Specify file in separation "' + line + '"')

    # save last file content
    if cur_file_path != "":
        separation.append((cur_file_path, ''.join(cur_file_lines)))

    # print information about separation
    separation_files = ', '.join([("'" + filepath + "'") for (filepath, _) in separation])

    return separation


def extract_timeout(comment_lines, condition):
    timeout = None
    for line in comment_lines:
        line = filter_line(line, TIMEOUT_FLAG, condition)
        if not line:
            continue
        timeout = float(line)
    return timeout


def extract_commands(comment_lines, condition, run_script):
    commands = []

    for command in comment_lines:
        command_info = filter_command_line(command, condition, run_script, configs.get_val("compatible"))
        if not command_info:
            continue
        commands.append(command_info)
    return commands


def extract_level(comment_lines, target_level, condition):
    if not target_level:
        return True

    found_flag = False
    for line in comment_lines:
        filtered_line = filter_line(line, LEVEL_FLAG, condition)
        if not filtered_line:
            continue

        found_flag = True
        if filter_level(filtered_line, target_level):
            return True
    return filter_level("0", target_level) if not found_flag else False


# If there is more than one 'compare %f' commands.
# Then they will be enumerated to distiguish them in `compare.py`.
# This needed to apply SCANs only after handled `compare`. 
def enumerate_compares(commands):
    def isCommandPipedIntoCompare(command):
        last = command['cmd'][-1]
        if command['PIPE'] and last.strip().startswith("compare"):
            return True
        return False
 
    count_of_compares = sum(1 for command in commands if isCommandPipedIntoCompare(command))
 
    i = 1
    if count_of_compares > 1:
        for command in commands:
            if isCommandPipedIntoCompare(command):
                command['cmd'][-1] += f' --compare_number={i}'
                i += 1
 
    return commands

def read_list(content):
    if not content:
        return {"*"}, {}
    include_flag = "[ALL-TEST-CASE]"
    exclude_flag = "[EXCLUDE-TEST-CASE]"
    case_list = set()
    exclude_case_list = set()
    is_exclude = False
    for line in content:
        line = line.strip()
        if str(line).startswith('#') or not line:
            continue
        if line.find(include_flag) != -1:
            is_exclude = False
        elif line.find(exclude_flag) != -1:
            is_exclude = True
        elif is_exclude:
            exclude_case_list.add(line)
        else:
            case_list.add(line)
    if not case_list:
        case_list = {"*"}
    return case_list, exclude_case_list


@total_ordering
class Result:
    def __init__(self, case, task, cfg, status, commands, commands_result, log_file):
        self.case = case
        self.task = task
        self.cfg = cfg
        self.time = None
        self.status = status
        self.commands = commands
        self.commands_result = commands_result
        self.log_file = log_file

    def gen_xml(self, root):
        from xml.etree import ElementTree

        case = ElementTree.SubElement(
            root,
            "testcase",
            name=str(self.case),
            classname="{}.{}".format(self.task, self.cfg),
        )

        if self.status == FAIL:
            failure = ElementTree.SubElement(case, "failure")
            if isinstance(self.commands_result, str):
                failure.text = "Test case preparation failed, "
                failure.text += self.commands_result
            else:
                failure.text = "List of commands:\n"
                for cmd in self.commands:
                    failure.text += "EXEC: {}\n".format(cmd)
                failure.text += "----\n"
                failure.text += self.command_result_to_text(self.commands_result[-1])
        elif self.status == UNRESOLVED:
            skipped = ElementTree.SubElement(case, "skipped")
            skipped.text = "No valid command statement was found."

    def command_result_to_text(self, result):
        text = "EXEC: {}\n".format(result.get("cmd"))
        text += "Return code: {}\n".format(result.get("return_code"))
        text += "Stdout: \n{}\n".format(result.get("stdout"))
        text += "Stderr: \n{}\n".format(result.get("stderr"))
        return text

    def gen_json_result(self):
        from collections import OrderedDict

        result = OrderedDict()
        result["name"] = "{}".format(self.case)
        result["cfg"] = "{}".format(self.cfg)
        result["result"] = self.status
        result["commands"] = self.commands
        result["output"] = self.commands_result
        result["log_file"] = self.log_file
        return result

    def __lt__(self, other):
        return self.case < other.case
