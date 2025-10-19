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
import argparse
import configparser
import locale
import os
import sys
import threading
import timeit
import re
import platform
import shlex
from functools import wraps
from pathlib import Path
from typing import Set

RUN_FLAG = "RUN"
EXEC_FLAG = "EXEC"
PIPE_KEY = 'PIPE'
SEPARATE_FILE_DIRECTIVE = 'SEPARATE-FILE'
EXIT_CODE = 'exit_code'
ERRCHECK_FLAG = "ERRCHECK"
ASSERT_FLAG = "ASSERT"
EXPECT_FLAG = "EXPECT"
DEPENDENCE_FLAG = "DEPENDENCE"
TIMEOUT_FLAG = "TIMEOUT"
LEVEL_FLAG = "LEVEL"
FLAGS = [RUN_FLAG, EXEC_FLAG, SEPARATE_FILE_DIRECTIVE, ERRCHECK_FLAG, ASSERT_FLAG,
        DEPENDENCE_FLAG, TIMEOUT_FLAG, EXPECT_FLAG, LEVEL_FLAG]
PASS = "PASS"
FAIL = "FAIL"
XFAIL = "XFAIL"
XPASS = "XPASS"
NOT_RUN = "NOT_RUN"
UNRESOLVED = "UNRESOLVED"
UNSUPPORTED = "UNSUPPORTED"
LOGIC_KEY_WORD = ["and", "or", "not", "True", "False"]
UNSUCCESSFUL = [FAIL, UNSUPPORTED, UNRESOLVED, NOT_RUN]
ALL = [PASS, FAIL, XFAIL, XPASS, UNSUPPORTED, UNRESOLVED]
DEFAULT_PRINT = [PASS, FAIL, XFAIL, XPASS, UNSUPPORTED]
RESULT = {
    PASS: 0,
    FAIL: 0,
    NOT_RUN: 0,
    UNRESOLVED: 0,
    XFAIL: 0,
    XPASS: 0,
}
BASE_DIR = Path(__file__).parent.absolute()

ENCODING = "utf-8"
OS_SEP = os.path.sep
OS = platform.system()
if OS == 'Windows' and ' ' in sys.executable:
    EXECUTABLE = '"' + sys.executable + '"'
else:
    EXECUTABLE = sys.executable
COMPARE = BASE_DIR / "compare.py"

PRINT_LOCK = threading.Lock()


def read_file(file_path):
    """Read files based on encoding and return all file lines

    :param file_path: Path
    :param encoding: str
    :return:
    """
    lines = []
    with file_path.open(encoding="utf-8") as file:
        all_lines = file.readlines()
    for line in all_lines:
        if line.strip():
            lines.append(line.strip())
    return lines


def read_config(file_path):
    """Read config file based on encoding and return test config"""
    if not file_path.exists() or not file_path.is_file():
        return None
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(str(file_path), encoding="utf-8")
    return config


def get_config_value(config, section, option):
    """Read config value from test config"""
    try:
        return config[section][option]
    except KeyError:
        return None


def config_section_to_dict(config, section):
    try:
        return {k: v for k, v in config.items(section)}
    except configparser.NoSectionError:
        return {}


def config_section_to_set(config, section):
    try:
        res = set()
        for k, v in config.items(section):
            temp = str(v).strip().split()
            for x in temp:
                if x in LOGIC_KEY_WORD:
                    raise Exception('[ERROR]Condition Key Word can not be "and","not","or"! Please modify!')
                res.add(x)
        return res
    except configparser.NoSectionError:
        return {}


def ls_all(path, suffix=None):
    """Output all files in a directory"""
    all_files = []
    _path = complete_path(path)
    if _path.is_file() and is_case(_path, suffix):
        return [_path]
    for name, _, files in os.walk(str(_path)):
        for file in files:
            if is_case(Path(name) / file, suffix):
                all_files.append(Path(name) / file)
    return all_files


def is_case(path, suffix):
    """Determine if it is a test case based on the suffix

    :param suffix: tuple
    :param path: Path
    :return:
    """
    if suffix is None:
        return True
    elif isinstance(suffix, str):
        return path.suffix[1:] == suffix
    return path.suffix[1:] in suffix


def split_and_complete_path(paths):
    """Split the paths and returns the canonical path of each path"""
    canonicalPaths = []
    for path in paths.split(","):
        canonicalPaths.append(complete_path(path))
    return canonicalPaths


def complete_path(path):
    """Returns the canonical path of a path"""
    path = Path(path)
    if not path.exists():
        return Path(os.path.realpath(str(path)))
    return path.expanduser().resolve()


def filter_line(line, flag=None, condition=None):
    """Returns the line starting with the flag"""
    if flag is None:
        return line
    if condition == None:
        line_flag = line.strip().split(":")[0].strip()
        if line_flag == flag:
            new_line = line.strip()[len(flag) + 1:].strip().lstrip(":").strip()
            return new_line
        return None
    else:
        line_flag = line.strip().split(":")[0].strip()
        cur_condition = re.match(r'\([0-9a-zA-Z\|\&\!\(\) ]+\)', line_flag)
        if cur_condition == None:
            if line_flag == flag:
                new_line = line.strip()[len(flag) + 1:].strip().lstrip(":").strip()
                return new_line
            return None
        else:
            cur_con = cur_condition.group()
            if process_condition(cur_con, condition):
                new_line_flag = line_flag.replace(cur_con, "").strip()
                if new_line_flag == flag:
                    new_line = line.strip()[len(line_flag) + 1:].strip().lstrip(":").strip()
                    return new_line
            else:
                return None


def filter_command_number(command: str):
    cmd = {}
    cmd.setdefault(EXIT_CODE, 0)
    cmd.setdefault(PIPE_KEY, False)
    if not re.match(r'^EXEC(-PIPE)?(-(-)?\d+)?$', command):
        sys.exit("""[ERROR] Only accept command like EXEC(-PIPE)(-number)!
Please check your command : {} """.format(command))
    number = 0
    if '-' in command:
        temp = command.split('-')
        if command.count('-') == 3:  # must be EXEC-PIPE--number
            number = - int(temp[-1])
            cmd[PIPE_KEY] = True
        elif command.count('-') == 2:
            if len(temp[1]) == 0:  # EXEC--number
                number = - int(temp[-1])
            else:  # EXEC-PIPE-number
                number = int(temp[-1])
                cmd[PIPE_KEY] = True
        elif command.count('-') == 1:
            if temp[-1] == 'PIPE':
                number = 0
                cmd[PIPE_KEY] = True
            else:
                number = int(temp[-1])
    cmd[EXIT_CODE] = number
    return cmd


# process signal negative number.
def process_exit_code(number):
    if number < 0:
        if sys.platform == 'linux':  # TODO: may should consider darwin?
            return 0x80 - number  # Transfer to uint8 number, -6 -> 134.
        else:
            return 0x80000000 - number  # Transfer to uint32 number for windows, -1 -> 4294967295.
    return number


def parse_condition_from_str_to_set(condition: str):
    res = set()
    if not condition:
        return res
    temp = condition.split(',')
    for x in temp:
        x = x.strip().strip("'")
        res.add(x)
    return res


def parse_level_from_str_to_set(level: str):
    res = set()
    if not level:
        return level
    temp = level.split(',')
    for x in temp:
        x = x.strip()
        if not x.isdigit() or not (0 <= int(x) <= 4):
            raise argparse.ArgumentTypeError("{} is not a level, the level should be between 0-4".format(x))
        res.add(x)
    return res


# ! is not, & is and, | is or.
def process_condition(cur_con: str, conditions: Set[str]) -> bool:
    """
    Parse conditional expressions
    Args:
        cur_con: conditional expressions
        conditions
    Returns:
        bool
    Raises:
        ValueError
    """
    original_expr = cur_con
    cur_con = (
        cur_con.replace("&", " and ")
        .replace("|", " or ")
        .replace("!", " not ")
    )

    words = re.findall(r'[0-9a-zA-Z_]+', cur_con)
    logic_ops = {'and', 'or', 'not'}

    for word in words:
        if word not in logic_ops:
            replacement = 'True' if word in conditions else 'False'
            cur_con = re.sub(rf'\b{word}\b', replacement, cur_con)

    remaining_words = re.findall(r'[a-zA-Z_]+', cur_con)
    allowed_words = logic_ops | {'True', 'False'}
    for word in remaining_words:
        if word not in allowed_words:
            raise ValueError(f"Illegal word '{word}' in expression: '{original_expr}'")

    try:
        return eval(cur_con)
    except SyntaxError as e:
        raise ValueError(f"Invalid syntax in '{original_expr}': {e}")


def precheck_flag(line_flag):
    res = all(x not in line_flag for x in FLAGS)
    return res


def filter_level(line: str, level: set) -> bool:
    return line in level


def filter_command_line(line: str, conditions: set, run_script: str, compatible: bool):
    """Returns and updates the command line starting with the flag"""
    line_flag = line.strip().split(":")[0].strip()
    if precheck_flag(line_flag):
        return None
    cur_con = re.match(r'\([0-9a-zA-Z\|\&\!\(\) ]+\)', line_flag)
    if cur_con != None:  # None condition means good.
        target = cur_con.group()
        if not process_condition(target, conditions):
            return None
        else:
            line = line.replace(target, " " * len(target))
            line_flag = line_flag.replace(target, "").strip()

    new_line = line.strip()[len(line_flag) + 1:].strip().lstrip(":").strip()

    # run with specific script.

    def escape_cmd(cmd: str):
        espace_words = '\\"$`'
        for i in espace_words:
            cmd = cmd.replace(i, '\\{}'.format(i))
        return cmd

    if (line_flag.startswith(EXEC_FLAG) or line_flag.startswith(ERRCHECK_FLAG)) and compatible:
        return None
    if line_flag.startswith(RUN_FLAG):
        line_flag = line_flag[len(RUN_FLAG) + 1:]
        if run_script is not None:
            redirect = False
            if '|' in run_script and 'ignore_cmd_redirect' in run_script:
                run_script = run_script[:run_script.rfind('|')]
                redirect = True
            if '|' in new_line and 'compare' in new_line:
                compare_part = new_line[new_line.rfind('|'):]
                actual_run_cmd = new_line[:new_line.rfind('|')]
                new_line = '{} "{}" {}'.format(run_script, escape_cmd(actual_run_cmd), compare_part)
                if redirect:
                    if '>' in actual_run_cmd:
                        cmd_list = actual_run_cmd.split()
                        index = 0
                        for i, cmd in enumerate(cmd_list):
                            if '%run' in cmd:
                                index = i
                                break
                        for i, cmd in enumerate(cmd_list):
                            if '>' in cmd and i > index:
                                index = i
                                break
                        actual_cmd = ' '.join(cmd_list[:index])
                        redirect_cmd = ' '.join(cmd_list[index:])
                    else:
                        actual_cmd = actual_run_cmd
                        redirect_cmd = ''
                    if platform.system() == "Windows":
                        new_line = '{} "{}" {} {}'.format(run_script, escape_cmd(actual_cmd), redirect_cmd, compare_part)
                    else:
                        new_line = '{} "{}" {} {}'.format(run_script, escape_cmd(actual_cmd), redirect_cmd, compare_part)
            else:  # new_line is a single command.
                new_line = '{} "{}"'.format(run_script, escape_cmd(new_line))
    if line_flag.startswith(EXEC_FLAG) and new_line:
        cmd = filter_command_number(line_flag)
        cmd.setdefault('cmd', new_line)
        if cmd[PIPE_KEY]:
            if new_line.count('|') != 1:
                # print("[INFO] Can not handle 0 or more than 1 `|` in {}:{}, handle it as EXEC.".format(line_flag,
                #                                                                                        new_line))
                cmd[EXIT_CODE] = 0
                cmd[PIPE_KEY] = False
            else:
                new_lines = new_line.split('|')
                cmd['cmd'] = new_lines
        return cmd
    elif line_flag == ERRCHECK_FLAG:
        cmd = {}
        cmd.setdefault('exit_code', 1)
        cmd.setdefault('PIPE', True)
        if platform.system() == "Windows":
            cmd['cmd'] = (new_line + " 2>&1 1>nul | compare %f").split('|')
        else:
            cmd['cmd'] = (new_line + " 2>&1 1>/dev/null | compare %f").split('|')
        return cmd
    return None


def split_comment(comment, lines):
    """Split text based on comments"""
    comment_lines = []
    uncomment_lines = []
    comment_len = len(comment)
    for line in lines:
        if line.strip()[:comment_len] == comment:
            if not precheck_flag(line.strip()[comment_len:]):
                comment_lines.append(line.strip()[comment_len:])
        else:
            uncomment_lines.append(line)
    return uncomment_lines, comment_lines


def add_run_path(new_path):
    """Add path to PATH"""
    run_env = os.environ.copy()
    old_path = run_env.get("PATH")
    if old_path:
        if sys.platform == 'linux' or sys.platform == 'darwin':
            run_env["PATH"] = old_path + ":" + new_path
        else:
            run_env["PATH"] = old_path + ";" + new_path
    else:
        run_env["PATH"] = new_path
    return run_env


def timer(func):
    """Decorator that reports the execution time."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = timeit.default_timer()
        result = func(*args, **kwargs)
        end = timeit.default_timer()
        safe_print(
            "Function: {}, args: {}, kwargs: {}, Time Consuming: {}s\n".format(
                func.__name__, str(args), str(kwargs), end - start
            )
        )
        return result

    return wrapper


def is_relative(path1, path2):
    """Is path1 relative to path2"""
    _p1 = complete_path(path1)
    _p2 = complete_path(path2)
    try:
        _p1.relative_to(_p2)
    except ValueError:
        return 0
    return 1


def merge_result(multi_results):
    for result in multi_results:
        if result in UNSUCCESSFUL:
            return result
    return PASS


def escape(special_chars, original_string):
    special_re = re.compile(
        "(" + "|".join(re.escape(char) for char in list(special_chars)) + ")"
    )
    special_map = {char: "\\%s" % char for char in special_chars}

    def escape_special_char(m):
        char = m.group(1)
        return special_map[char]

    return special_re.sub(escape_special_char, original_string)


def quote(original_string):
    if platform.system() == "Windows":
        return '"' + escape('\\"', original_string) + '"'
    else:
        return shlex.quote(original_string)


def safe_print(*args):
    with PRINT_LOCK:
        print(*args)
