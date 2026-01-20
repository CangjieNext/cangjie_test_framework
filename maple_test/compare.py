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
import logging
import re
import sys
import difflib
import platform
from textwrap import indent
from functools import partial

from utils import complete_path, process_condition, parse_condition_from_str_to_set, escape, safe_print

ASSERT_FLAG = "ASSERT"
EXPECTED_FLAG = "EXPECTED"
EXPECTED_REGEX = r"\:{line_num}\:.*\:.*"
PATH_PATTERN = r'(/[^<>"\\|?]+)+\:\d+'

SCAN_KEYWORDS = ["full", "not", "begin", "next", "end", "after", "txt"]
REGEX_KEYWORDS = ["auto", "not", "begin", "next", "end", "after"]
EXPECTED_KEYWORDS = ["regex", "regex-auto", "regex-not"]

# These codes are used to replace color names in the expected text like `{COLOR=RED}...{/COLOR}`
# with special escape symbols, the same as for the console output
# The example of replacement: {COLOR=RED} => \u{1B}[31m
# Keep consistent with colors defined in `cangjie/libs/std/unittest/pretty_console.cj`
COLOR_CODES = { "RED": 31, "GREEN": 32, "YELLOW": 33, "BLUE": 34, "MAGENTA": 35, "CYAN": 36, "GRAY": 90 }

TRANSFER_BLACK_LIST = ["Internal error"]
global_group_dict = dict()

IS_WINDOWS = True if platform.system() == "Windows" else False
multiline_pattern = r'(SCAN(-IN|-TXT)*)'
multiscan_pattern = r'/\*\s*SCAN'


class CompareError(Exception):
    pass


def check_condition(compare_lines, conditions):
    res = []
    for line in compare_lines:
        src = line[0]
        if src.startswith(ASSERT_FLAG) or src.startswith(EXPECTED_FLAG):
            res.append(line)
            continue
        else:
            cur_con = re.match(r'\([0-9a-zA-Z_\|\&\!\(\) ]+\)', src)
            if cur_con and process_condition(cur_con.group(), conditions):
                tmp = line.copy()
                tmp[0] = tmp[0].replace(cur_con.group(), "")
                res.append(tmp)
    return res


# input_str is file,  expect_str is stdin.
def multiline_check(input_str, expect_str: str, in_mode, txt_mode):
    def print_error(a, b):
        d = difflib.Differ()
        diff = d.compare(a, b)
        try:
            safe_print('\n'.join(list(diff)))
        except Exception as e:
            safe_print('\nMultiLine SCAN-IN Compare Failed!')
            safe_print("[ERROR] Output string print error. {}".format(e.args))

    if IS_WINDOWS and not txt_mode:
        if re.findall(PATH_PATTERN, input_str):
            input_str = input_str.replace('/', '\\')
            expect_str = expect_str.replace('/', '\\')

    if in_mode:  # in mode.
        input_str = input_str.strip()  # remove \n.
        if len(input_str) != 0 and input_str in expect_str:
            return True
        else:
            print_error(input_str.splitlines(), expect_str.splitlines())
            return False
    else:  # not in mode, all match mode.
        i_lines = input_str.splitlines()
        e_lines = expect_str.splitlines()
        if len(i_lines) != len(e_lines):
            print_error(i_lines, e_lines)
            return False
        else:
            l = len(i_lines)
            for i in range(0, l):
                if i_lines[i] != e_lines[i]:
                    print_error(i_lines, e_lines)
                    return False
        return True


def main():
    opts = parse_cli()
    case_path = opts.case_path
    com_opt = opts.com_opt
    comment = opts.comment
    condition = parse_condition_from_str_to_set(opts.condition)
    compare_object = opts.compare_object
    assert_flags = opts.assert_flag
    transfer = opts.transfer
    compare_number = opts.compare_number
    if not assert_flags:
        assert_flags.append(ASSERT_FLAG)
    expected_flags = opts.expected_flag
    if not expected_flags:
        expected_flags.append(EXPECTED_FLAG)
    try:
        content = compare_object.read()
    except UnicodeDecodeError as e:
        safe_print("Wrong stdin encoding:{}\n{}".format(e.object, e))
        sys.exit(1)
    content_line_map = gen_line_map(content)
    safe_print("compare.py input:")
    safe_print(indent(content, "\t", lambda line: True))
    safe_print("compare.py input end\n")

    if compare_object.isatty():
        sys.stderr.write("ERROR: require compare objects, filepath or stdin \n")
        sys.exit(253)
    compare_line_regex = gen_compare_regex(comment, assert_flags, expected_flags)
    compare_lines = extract_compare_lines(case_path, compare_line_regex)
    compare_lines = check_condition(compare_lines, condition)
    multiline_compares = parse_all_multiline_comment(case_path, compare_number)
    compare_result = True
    start = 0
    if not compare_lines and not multiline_compares:
        safe_print("[ERROR]`ASSERT` or `EXPECTED` or 'SCAN' key words not found in your case!")
        sys.exit(1)
    if com_opt == 'O2':
        patterns = [r':[0-9]+:[0-9]+:', r':[0-9]+:', r':[0-9]+']
        for pattern in patterns:
            x = re.compile(pattern)
            for y in range(len(compare_lines)):
                if 'regex' in compare_lines[y][0]:
                    compare_lines[y][0] = x.sub(pattern, compare_lines[y][0])
                elif 'scan' in compare_lines[y][0]:
                    compare_lines[y][0] = x.sub(pattern, compare_lines[y][0]).replace('scan', 'regex')
    if compare_lines:
        safe_print("Starting SingleLine Compare:")
    for compare_line in compare_lines:
        output_line_num = text_index_to_line_num(content_line_map, start)
        compare_line, line_num = compare_line
        flag, compare_pattern = split_compare_line(compare_line)
        pattern_flag, pattern = split_pattern_line(compare_pattern)

        info = ""
        keywords = pattern_flag.split("-")
        if flag.strip() in assert_flags:
            info = "It's a assert, "
        elif flag.strip() in expected_flags:
            if "auto" in keywords:
                pattern = r"\s+".join([re.escape(word) for word in pattern.split()])
                keywords.remove("auto")
            pattern = EXPECTED_REGEX.format(line_num=line_num) + pattern
            if pattern_flag.strip() not in EXPECTED_KEYWORDS:
                raise CompareError(
                    "Unsupport expected keywords: {!r}".format(pattern_flag)
                )
        else:
            raise CompareError("Unsupport flag: {!r}".format(flag))
        count = -1
        for keyword in keywords:
            if keyword.isnumeric():
                count = int(keyword)
        match_func = gen_match_func(keywords)
        if "next" not in keywords and "end" not in keywords and "after" not in keywords:
            start = 0
        if "scan" in keywords:
            single_txt = True if "txt" in keywords else False
            if IS_WINDOWS and not single_txt:
                if re.findall(PATH_PATTERN, pattern):
                    pattern = pattern.replace('/', '\\\\')
        pattern = update_pattern(pattern)
        result, start = match_func(content, content_line_map, pattern, start, count=count)
        info += "flag: {}, pattern: {} , result: {}, matched at output line: {} ".format(
            pattern_flag, pattern, result, output_line_num
        )
        safe_print(info.encode(encoding='utf-8', errors='ignore'))
        safe_print('back reference dict:{}'.format(global_group_dict))
        if result is False:
            safe_print("SingleLine Compare Failed")
        else:
            safe_print('SingleLine Compare End')
        compare_result &= result
    if multiline_compares:  # only support write once.
        index = 1
        for i in multiline_compares:
            safe_print("Start MultiLine Compare {}: {} ...".format(index, i[:min(20, len(i))]))
            index += 1
            start = re.match(r'/\*\s*' + multiline_pattern + r'\n', i)
            multi_str = i[len(start.group()):-2]  # -2 is len of '*/'
            multi_str = handle_ansi_attributes(multi_str)
            res = multiline_check(input_str=multi_str, expect_str=content, in_mode='-IN' in start.group(),
                                  txt_mode='-TXT' in start.group())
            if not res:
                compare_result = False
    diagkind = re.findall(r'("DiagKind": .*")', str(content))
    if transfer:
        safe_print("[WARNING] trying to transfer cur case {} into multi line compare case.".format(transfer))
        with open(transfer, 'r', encoding='utf-8') as f:
            src = f.read()
            pattern = r'(//.*ASSERT.*|//.*EXPECTED.*)'
            new_content = re.sub(pattern, "", src).rstrip()
            new_content = re.sub(r'/\*.*SCAN[\s\S]*\*/', "", new_content, re.M).rstrip()
            content = re.sub(pattern, "", str(content))  # delete compare keyword part in multi line compare.
            if multiline_compares:  # delete old multi line compare.
                for multiline_compare in multiline_compares:
                    new_content = new_content.replace(multiline_compare, "").rstrip()
            for bad_words in TRANSFER_BLACK_LIST:
                if bad_words in content:
                    raise Exception('Unexpected output <{}> found! Please update case manually!'.format(bad_words))
            if len(diagkind) == 0:
                new_content = new_content + "\n\n/* SCAN\n{}*/\n".format(content)
            else:
                for diag in diagkind:
                    diag = diag.split("\": \"")[1].rstrip("\"")
                    if not diag in new_content:
                        new_content = new_content.rstrip() + "\n// ASSERT: scan {}\n".format(diag)
        with open(transfer, 'w', encoding='utf-8') as f:
            f.write(new_content)
        safe_print("[WARNING] {} transfer into multi line compare case done.".format(transfer))
    if compare_result is True:
        safe_print("[Compare Pass]")
        return 0
    else:
        safe_print("[Compare Fail]")
    sys.exit(1)


def handle_ansi_attributes(input_str):
    colors_stack = []

    def replace_color(match):
        color_name_to_set = match.group("color")
        if color_name_to_set:
            if color_name_to_set not in COLOR_CODES:
                raise ValueError("Unsupported color '%s' in color directive. Supported colors: %s"
                                 % (color_name_to_set, ", ".join(COLOR_CODES.keys())))
            colors_stack.append(color_name_to_set)
            return "\x1b[%dm" % COLOR_CODES[color_name_to_set]
        elif match.group("unset_color"):
            if len(colors_stack) == 0:
                raise ValueError("There is no corresponding set color directive for the unset directive {/COLOR}.")
            colors_stack.pop()
            set_previous_color_directive = "\x1b[%dm" % COLOR_CODES[colors_stack[-1]] if len(colors_stack) > 0 else ""
            return "\x1b[0m%s" % set_previous_color_directive
        elif match.group("escape"):
            return "\x1b"
        else:
            raise ValueError("The ansi code directive should be either {COLOR=<color_name>} or {/COLOR}")

    return re.sub(r"{(?:COLOR=(?P<color>\w+)|(?P<unset_color>/COLOR)|(?P<escape>ESC))}", replace_color, input_str)


def split_compare_line(compare_line):
    if len(compare_line.lstrip().split(":", 1)) < 2:
        safe_print(
            "Please check compare line, found compare flag but no actual compare content!!!"
        )
        raise CompareError(
            "Please check compare line, found compare flag but no actual compare content!!!"
        )
    else:
        return compare_line.lstrip().split(":", 1)


def split_pattern_line(compare_pattern):
    try:
        pattern_flag, pattern = compare_pattern.lstrip().split(" ", 1)
    except ValueError:
        pattern_flag = compare_pattern.lstrip()
        pattern = ""
    return pattern_flag, pattern


begin_case = False


def gen_match_func(keywords):
    global begin_case
    valid_keywords = []
    assert_mode = keywords[0]
    match_func = None
    if assert_mode == "scan":
        match_func = scan_match
        valid_keywords = SCAN_KEYWORDS
    elif assert_mode == "regex":
        match_func = regex_match
        valid_keywords = REGEX_KEYWORDS
    else:
        raise CompareError("scan/regex mode: {} is not valid".format(assert_mode))
    for keyword in keywords[1:]:
        if keyword not in valid_keywords and not keyword.isnumeric():
            raise CompareError(
                "keyword: {} is not valid for {}".format(keyword, assert_mode)
            )
        if keyword == "auto":
            match_func = partial(auto_regex_match, match_func=match_func)
        elif keyword == "not":
            match_func = partial(not_match, match_func=match_func)
        elif keyword == "next":
            if not begin_case:
                raise Exception("Please use `next` after `begin`!")
            match_func = partial(next_match, match_func=match_func)
        elif keyword == "after":
            if not begin_case:
                raise Exception("Please use `after` after `begin`!")
            match_func = partial(after_match, match_func=match_func)
        elif keyword == "begin":
            begin_case = True
            match_func = partial(begin_match, match_func=match_func)
        elif keyword == "end":
            match_func = end_match
        elif keyword == "full":
            match_func = full_match
        elif keyword.isnumeric():
            match_func = partial(num_match, match_func=match_func)
    return match_func


def update_pattern(pattern):
    if len(global_group_dict.keys()) != 0:
        for i in global_group_dict.keys():
            pattern = pattern.replace('(?P={})'.format(i), global_group_dict[i])
    return pattern


def is_valid_pattern(pattern):
    try:
        re.compile(pattern)
    except re.error:
        logging.error("Error pattern: {!r}".format(pattern))
        return False
    except TypeError:
        logging.error(type(pattern), repr(pattern))
    return True


def regex_match(content, line_map, pattern, start=0, count=-1):
    if not is_valid_pattern(pattern):
        raise CompareError("Not valid pattern: {!r}".format(pattern))
    matches = re.finditer(str(pattern), content, re.MULTILINE)
    end = 0
    if count == -1:
        for _, match in enumerate(matches, start=1):
            for i in match.groupdict():
                global_group_dict.update({i: match.groupdict()[i]})
            end = match.end() + start
            line_num = text_index_to_line_num(line_map, end)
            if line_num + 1 >= len(line_map):
                return True, end
            return True, line_map[line_num] + 1
        return False, start
    else:
        x = re.findall(pattern, content)
        if len(x) != count:
            return False, start
        else:
            return True, end


def scan_match(content, line_map, pattern, start=0, match_func=regex_match, count=-1):
    line_num = text_index_to_line_num(line_map, start)
    pattern = re.sub(r'([^\u0100-\uffff]+)',
                     lambda x: (x.group(1) + r' ').encode("utf-8").decode("unicode_escape")[:-1], pattern)
    if count == -1:
        if content.find(pattern) != -1:
            end = content.find(pattern) + start
            line_num = text_index_to_line_num(line_map, end)
            return True, line_map[line_num] + 1
        return False, start
    else:
        if content.count(pattern) != count:
            return False, start
        return True, line_map[line_num] + 1


def begin_match(content, line_map, pattern, start=0, match_func=regex_match, count=-1):
    return match_func(content, line_map, pattern, start=0)


def auto_regex_match(content, line_map, pattern, start=0, match_func=regex_match, count=-1):
    pattern = r"\s+".join([re.escape(word) for word in pattern.split()])
    return match_func(content, line_map, pattern, start)


def not_match(content, line_map, pattern, start=0, match_func=regex_match, count=-1):
    result, end = match_func(content, line_map, pattern, start)
    if not result:
        line_num = text_index_to_line_num(line_map, start)
        return not result, line_map[line_num] + 1
    return not result, start


def next_match(content, line_map, pattern, start=0, match_func=regex_match, count=-1):
    line_num = text_index_to_line_num(line_map, start)
    return match_func(content.splitlines()[line_num], line_map, pattern, start)


def after_match(content, line_map, pattern, start=0, match_func=regex_match, count=-1):
    line_num = text_index_to_line_num(line_map, start)
    return match_func('\n'.join(content.splitlines()[line_num:]), line_map, pattern, start)


def end_match(content, line_map, pattern, start=0, match_func=regex_match, count=-1):
    line_num = text_index_to_line_num(line_map, start)
    if line_num < len(line_map):
        return False, start
    return True, start


def full_match(content, line_map, pattern, start=0, match_func=regex_match, count=-1):
    line_num = text_index_to_line_num(line_map, start)
    pattern = re.sub(r'([^\u0100-\uffff]+)',
                     lambda x: (x.group(1) + r' ').encode("utf-8").decode("unicode_escape")[:-1], pattern)
    if content != pattern:
        return False, start
    return True, line_map[line_num] + 1


def num_match(content, line_map, pattern, start=0, match_func=regex_match, count=-1):
    return match_func(content, line_map, pattern, start, count=count)


def gen_line_map(text):
    regex = ".*\n?"
    line_map = []
    for match in re.finditer(regex, text):
        line_map.append(match.end())
    return line_map


def text_index_to_line_num(line_map, index):
    for line_num, end in enumerate(line_map):
        if end >= index:
            return line_num
    return line_num + 1


def gen_compare_regex(comment, assert_flags, expected_flag):
    regex = ""
    for flag in expected_flag:
        excepted_regex = r"(?:{comment}\s*)(.*{flag}[\t ]*\:[\t ]*.*$)".format(  # check condition later
            comment=escape("\\$()*+.[]?^{}|", comment), flag=flag
        )
        if regex != "":
            regex = "{}|{}".format(regex, excepted_regex)
        else:
            regex = excepted_regex
    for flag in assert_flags:
        assert_regex = r"(?:{comment}\s*)(.*{flag}[\t ]*\:[\t ]*.*$)".format(  # check condition later
            comment=escape("\\$()*+.[]?^{}|", comment), flag=flag
        )
        if regex != "":
            regex = "{}|{}".format(regex, assert_regex)
        else:
            regex = assert_regex
    return regex


def extract_compare_lines(file_path, regex):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    matches = re.finditer(regex, content, re.MULTILINE)
    compare_lines = []
    end_regex = ".*\n?"
    line_map = []
    for match in re.finditer(end_regex, content):
        line_map.append(match.end())
    for match in matches:
        for group_num in range(0, len(match.groups())):
            group_num = group_num + 1
            if match.group(group_num) is None:
                continue
            for line_num, end in enumerate(line_map):
                if end > match.start(group_num):
                    compare_lines.append([match.group(group_num), line_num + 1])
                    break
    return compare_lines


multi_L = '/*'
multi_R = '*/'


def parse_all_multiline_comment(file, compare_number):
    with open(file, 'r', encoding='utf-8') as f:
        if compare_number == -1:
            contents = f.read()
        else:
            contents = read_scans(f, compare_number)
        all_match = []
        found = re.search(multiscan_pattern, contents)
        if not found:
            return

        start_index = found.start()
        temp_stack = [start_index]
        for i in range(start_index + 1, len(contents) - 1):
            if contents[i:i + 2] == multi_R:
                if temp_stack:
                    last_index = temp_stack.pop()
                    if not temp_stack:
                        all_match.append([last_index, i + 2])

            elif contents[i:i + 2] == multi_L:
                temp_stack.append(i)

        res = []
        for i in range(len(all_match) - 1, -1, -1):
            cur = all_match[i]
            if not re.match(multiscan_pattern, contents[cur[0]:cur[1]]):
                all_match.remove(cur)
            else:
                res.append(contents[cur[0]:cur[1]])

        return res

def read_scans(file, compare_number):
    compares_above = 0
    content = ""
    for line in file:
        if compares_above > compare_number:
            break
        if line.find("| compare %f") != -1:
            compares_above += 1
        if compares_above == compare_number:
            content += line
 
    return content

def parse_cli():
    parser = argparse.ArgumentParser(prog="compare.py")
    parser.add_argument("--comment", help="Test case comment")
    parser.add_argument(
        "--assert_flag",
        help="Test case assert flag, default ASSERT",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--expected_flag",
        help="Test case expected flag for compile, default EXCEPTED",
        action="append",
        default=[],
    )
    parser.add_argument(
        "case_path", type=complete_path, help="Source path: read compare rules"
    )
    parser.add_argument(
        "--compare_number", type=int, nargs='?', default=-1,
        help="Number of 'compare %%f' pipe in file after which SCANs will be checked. All SCANs is checked by default."
    )
    parser.add_argument(
        "com_opt", type=str, nargs='?', default='', help="Compile option of this case, default empty."
    )
    parser.add_argument(
        "--condition", type=str, nargs='?', default='', help="Compare condition for Keyword, default empty."
    )
    parser.add_argument(
        "--compare_object",
        nargs="?",
        default=sys.stdin,
        help="compare object, default stdin",
    )
    parser.add_argument(
        "--transfer",
        help="Base dir for transfer/update normal case to multiline case.",
        type=str,
        default="",
    )
    opts = parser.parse_args()
    return opts


if __name__ == "__main__":
    logging.basicConfig(
        format="\t%(message)s", level=logging.DEBUG, stream=sys.stderr,
    )
    main()
