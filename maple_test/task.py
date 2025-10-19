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
import copy
import datetime
import multiprocessing
import platform
import shutil
import time
from collections import defaultdict, OrderedDict
from pathlib import Path
import sys
import os
import uuid
from configparser import ConfigParser
from maple_test import configs
from maple_test.run import run_commands, progress, TestError
from maple_test.test import Case, read_list
from maple_test.utils import (
    EXECUTABLE,
    COMPARE,
    PASS,
    FAIL,
    NOT_RUN,
    UNRESOLVED,
    DEFAULT_PRINT,
    OS_SEP,
    PIPE_KEY,
    EXIT_CODE
)
from maple_test.utils import (
    read_config,
    config_section_to_dict,
    config_section_to_set,
    get_config_value,
    ls_all,
    complete_path,
    split_and_complete_path,
    is_relative,
    quote,
    safe_print,
)

CONFIG_SET = set()

directory_dict = dict()

OVERWRITE_FILE = True

OVERWRITE_LEVEL_FILE = True

is_initialized = False


def ensure_config_initialized():
    global is_initialized
    if not is_initialized:
        _, _, _ = configs.init_config()
        is_initialized = True


class TaskConfig:
    def __init__(self, path, config: ConfigParser, user_config=None, user_env=None):
        safe_print("Reading config file:", path)
        if path in CONFIG_SET:
            raise Exception("config file inheritance cycle detected!")
        CONFIG_SET.add(path)

        self.path = complete_path(path)
        if config.has_section("inherit"):
            super_config_path = self.path.parent / get_config_value(config, "inherit", "inherit").strip()
            super_config = TaskConfig(super_config_path, read_config(super_config_path))
            self.inherit_top_config(super_config)
            name = str(path.relative_to(super_config.path.parent)).replace(OS_SEP, "_")
        else:
            name = path.name
            self.internal_var = {}
            self.env = {}
            self.suffix_comments = {}

        self.name = name.replace(".", "_")
        if config.has_section("root") and "path" in config["root"].keys():
            self.base_dir = self.path.parent / config["root"]["path"]
        else:
            self.base_dir = self.path.parent

        self.condition = set()
        self.update_sub_config(config)
        self.update_by_user_config(user_config, user_env)
        if config.has_section("run"):
            self.run_script = get_config_value(config, "run", "script").strip()
        else:
            self.run_script = None

    def inherit_top_config(self, top_config):
        self.internal_var = copy.deepcopy(top_config.internal_var)
        self.env = copy.deepcopy(top_config.env)
        self.suffix_comments = copy.deepcopy(top_config.suffix_comments)

    def update_by_user_config(self, user_config, user_env):
        if user_config is None:
            user_config = {}
        if user_env is None:
            user_env = {}
        self.internal_var.update(user_config)
        self.env.update(user_env)

    def update_sub_config(self, config):
        if self.path.exists():
            self.internal_var.update(config_section_to_dict(config, "internal-var"))
            self.suffix_comments.update(config_section_to_dict(config, "suffix"))
            self.condition.update(config_section_to_set(config, "condition"))
            envs = config_section_to_dict(config, "env")
            for i in envs:
                os.environ[i] = os.path.expandvars(envs[i])
                self.env.update({i: os.path.expandvars(envs[i])})
        else:
            safe_print(
                "config file: {}, not exists, will use upper config".format(self.path)
            )

    def get_case_config(self, case):
        case_config = {
            "internal_var": copy.deepcopy(self.internal_var),
            "env": copy.deepcopy(self.env),
        }
        case_config["internal_var"]["f"] = str(case.path.name)
        case_config["internal_var"]["n"] = str(case.path.stem)
        return case_config

    def __repr__(self):
        return str(self.name)


class TestSuiteTask:
    def __init__(self, test_path, cfg_path, running_config, condition, level, cli_running_config=None):
        ensure_config_initialized()
        if configs.get_val("compatible") and running_config.get("directory_list"):
            if not directory_dict:
                with open(str(running_config["directory_list"]), "r") as f:
                    content = f.read()
                    if not content:
                        raise TestError(
                            "Test suites directory list file:{} is empty, skip!!!!!".format(running_config["directory_list"])
                        )
                    for line in content.strip().splitlines():
                        key, value = line.strip().split()
                        directory_dict[key] = value
        elif configs.get_val("compatible") and not running_config.get("directory_list"):
            raise TestError(
                "Not found Test suites directory list, please enter \"--directory_list <DIRECTORY_LIST_PATH>\", skip!!!!!"
            )
        if cli_running_config is None:
            cli_running_config = {}
        self.run_split = cli_running_config.get('run_split')
        self.path = complete_path(test_path)
        self.cfg_path = cfg_path
        self.running_config = running_config
        self.condition = condition
        self.level = level
        config = read_config(self.cfg_path)
        if config is None:
            raise TestError(
                "Test suite config path:{} not found, skip!!!!!".format(self.cfg_path)
            )
        try:
            self.name = config["description"]["title"].replace(" ", "")
        except KeyError:
            self.name = self.path.name
        self.suffix_comments = config_section_to_dict(config, "suffix")

        self.result = defaultdict(int)

        self.task_set = defaultdict(list)
        self.task_set_result = {}
        self.all_cases = {}
        self.cost_time_info = {}
        self.config = None
        self._form_task_set(running_config, cli_running_config)

    def _form_task_set(self, running_config, cli_running_config):
        logger = configs.LOGGER
        user_test_list = cli_running_config.get("test_list")
        user_config = cli_running_config.get("user_config")
        user_env = cli_running_config.get("user_env")
        raw_top_config = read_config(self.cfg_path)
        self.config = TaskConfig(
            self.cfg_path, raw_top_config, user_config, user_env
        )
        self.condition.update(self.config.condition)
        if user_test_list is None:
            top_testlist_path = self._get_testlist(raw_top_config, self.config.base_dir)
        else:
            top_testlist_path = user_test_list
        if self.level:
            int_level = {int(x) for x in self.level}
            logger.info("LEVEL:{}".format(int_level))
        logger.info("CONDITION:{}".format(self.condition))
        name = self.config.name
        base_dir = self.config.base_dir
        testlist_path = top_testlist_path
        run_script = self.config.run_script
        self.task_set_result[name] = OrderedDict(
            {PASS: 0, FAIL: 0, NOT_RUN: 0, UNRESOLVED: 0}
        )
        if self.path.is_file():  # Single case input, don`t scan testlist, just run it!
            comment = self.suffix_comments[self.path.name.split('.')[-1]]
            case = Case(self.path, self.path, comment, self.condition, run_script, self.level)
            if case.relative_path != '':
                task = SingleTask(case, self.config, running_config, self.condition)
                self.task_set[name].append(task)
                self.task_set_result[name][task.result[0]] += 1
        else:
            if self.run_split is None:
                for case in self._search_list(base_dir, testlist_path):
                    task = SingleTask(case, self.config, running_config, self.condition)
                    self.task_set[name].append(task)
                    self.task_set_result[name][task.result[0]] += 1
            else:
                run_num = self.run_split[0]
                split_num = self.run_split[1]
                temp_count = 1
                for case in sorted(self._search_list(base_dir, testlist_path), key=lambda x: x.name):
                    if (temp_count + run_num) % split_num == 0:
                        task = SingleTask(case, self.config, running_config, self.condition)
                        self.task_set[name].append(task)
                        self.task_set_result[name][task.result[0]] += 1
                    temp_count += 1
        if sum([len(case) for case in self.task_set.values()]) < 1:
            logger.info(
                "Path %s not in testlist, be sure add path to testlist", str(self.path),
            )

    @staticmethod
    def _get_testlist(config, base_dir):
        testlist_path = []
        temp_path = get_config_value(config, "testlist", "path")
        if temp_path is None:
            testlist_path.append(base_dir / "testlist")
        else:
            for path in split_and_complete_path(temp_path):
                testlist_path.append(path)
        return testlist_path

    def _search_list(self, base_dir, testlist_paths):
        logger = configs.LOGGER
        suffixes = self.suffix_comments.keys()
        temp = []
        if testlist_paths:
            for testlist_path in testlist_paths:
                with open(testlist_path, 'r', errors='ignore', encoding='UTF-8-sig') as cases:
                    content = cases.readlines()
                    temp += content
        include, exclude = read_list(temp)
        cases = []
        all_test_case, exclude_test_case = self._search_case(
            include, exclude, base_dir, suffixes
        )
        case_files = set()
        for pattern in all_test_case:
            _cases = all_test_case[pattern]
            if _cases:
                case_files.update(_cases)
            else:
                logger.info(
                    "Testlist: {}, ALL-TEST-CASE: {} is invalid test case".format(
                        [i.name for i in testlist_paths], pattern
                    )
                )
        for pattern in exclude_test_case:
            _cases = exclude_test_case[pattern]
            if _cases:
                case_files -= _cases
            else:
                logger.info(
                    "Testlist: {}, EXCLUDE-TEST-CASE: {} is invalid test case".format(
                        [i.name for i in testlist_paths], pattern
                    )
                )

        if self.path.is_file():
            case_files = [self.path]
        else:
            case_files = [
                file.relative_to(self.path)
                for file in case_files
                if is_relative(file, self.path)
            ]
        for case_file in case_files:
            case_name = str(case_file)
            try:
                comment = self.suffix_comments[case_file.suffix[1:]]
            except KeyError:
                sys.exit("[ERROR] Test case path invalid!")
            if case_name not in self.all_cases:
                case = Case(case_file, self.path, comment, self.condition, self.config.run_script, self.level)
                if case.relative_path != '':
                    self.all_cases[case_name] = case
            if case_name in self.all_cases:
                cases.append(self.all_cases[case_name])
        return cases

    @staticmethod
    def _search_case(include, exclude, base_dir, suffixes):
        case_files = set()
        all_test_case = {}
        exclude_test_case = {}
        for glob_pattern in include:
            all_test_case[glob_pattern] = set()
            for include_path in base_dir.glob(glob_pattern):
                case_files.update(ls_all(include_path, suffixes))
                all_test_case[glob_pattern].update(ls_all(include_path, suffixes))
        for glob_pattern in exclude:
            exclude_test_case[glob_pattern] = set()
            for exclude_path in base_dir.glob(glob_pattern):
                case_files -= set(ls_all(exclude_path, suffixes))
                exclude_test_case[glob_pattern].update(ls_all(exclude_path, suffixes))
        return all_test_case, exclude_test_case

    def serial_run_task(self):
        for tasks_name in self.task_set:
            for index, task in enumerate(self.task_set[tasks_name]):
                if task.result[0] == PASS or task.result[0] == UNRESOLVED:
                    continue
                self.task_set_result[tasks_name][task.result[0]] -= 1
                _, task.result = run_commands(
                    (tasks_name, index),
                    task.result,
                    task.commands,
                    **task.running_config
                )
                if configs.get_val("fail_verbose"):
                    self.output_failed((_, task.result))
                status = task.result[0]
                cost_time = task.result[-1]
                self.task_set_result[tasks_name][status] += 1
                self.cost_time_info[task] = cost_time
        self.form_cost_time()

    def output_failed(self, result):
        output_template = (
            "\n--------\n"
            "TestCase Failed: \n"
            "Name           : {name}\n"
            "CMD list       : \n--------\n"
            "{cmd_list}"
            "--------\n"
            "Output         : \n{cmd_output}"
            "--------\n"
        )

        cmd_list_template = "{0: <15}:{1}\n"

        cmd_template = (
            "\n"
            "CMD            : {cmd}\n"
            "Return code    : {return_code}\n"
            "Stdout         : {stdout}\n"
            "Stderr         : {stderr}\n"
        )

        postion, result = result
        case = self.task_set[postion[0]][postion[1]]
        output = {}
        output["name"] = str(case)
        output["cmd_list"] = ""
        output["cmd_output"] = ""
        if result[0] == PASS:
            return
        if result[0] != PASS and not isinstance(result[1], str):
            for cmd_result in result[1]:
                output["cmd_output"] += cmd_template.format(**cmd_result)
            for cmd in case.commands[: len(result[1]) - 1]:
                output["cmd_list"] += cmd_list_template.format(PASS, cmd)
            output["cmd_list"] += cmd_list_template.format(
                FAIL, case.commands[len(result[1]) - 1]
            )
            for cmd in case.commands[len(result[1]):]:
                output["cmd_list"] += cmd_list_template.format(NOT_RUN, cmd)
        else:
            output["cmd_list"] = "Test case preparation failed, " + result[1] + "\n"
            output["cmd_output"] = output["cmd_list"]
        try:
            out = output_template.format(**output)
            if platform.system() == "Windows":
                out = out.encode('utf-8').decode('utf-8').encode('gbk', 'ignore').decode('gbk')
            safe_print(out)
        except UnicodeEncodeError as e:
            warning_message = "WARNING: {} {} {}".format(output["name"], e, e.args)
            if platform.system() == 'Windows':
                warning_message = warning_message.encode('utf-8').decode('utf-8').encode('gbk', 'ignore').decode('gbk')
            safe_print(warning_message)

    def parallel_run_task(self, process_num):
        multiprocessing.freeze_support()
        pool = multiprocessing.Pool(min(multiprocessing.cpu_count(), process_num))
        result_queue = []
        if configs.get_val("fail_verbose"):
            callback_func = self.output_failed
        else:
            callback_func = None
        for tasks_name in self.task_set:
            for index, task in enumerate(self.task_set[tasks_name]):
                if task.result[0] == PASS or task.result[0] == UNRESOLVED:
                    continue
                result_queue.append(
                    pool.apply_async(
                        run_commands,
                        args=((tasks_name, index), task.result, task.commands,),
                        kwds=task.running_config,
                        callback=callback_func,
                    )
                )
        progress(result_queue, configs.get_val("progress"))
        pool.close()
        pool.join()

        res_queue = []
        for result in result_queue:
            try:
                res = result.get()
                res_queue.append(res)
            except PermissionError as e:
                safe_print("{} {} {}".format(e, e.filename, e.filename2))
                continue
        result_queue = res_queue
        for position, result in result_queue:
            tasks_name, index = position
            task = self.task_set[tasks_name][index]
            self.task_set_result[tasks_name][task.result[0]] -= 1
            task.result = result
            self.task_set_result[tasks_name][result[0]] += 1
            self.cost_time_info[task] = result[-1]
        self.form_cost_time()

    def form_cost_time(self):
        name = os.path.join(os.path.dirname(self.cfg_path), 'cost_time.csv')
        with open(name, 'w') as f:
            for i in self.cost_time_info:
                if isinstance(self.cost_time_info[i], str):
                    f.write('{},{}\n'.format(i, self.cost_time_info[i]))
                elif isinstance(self.cost_time_info[i], datetime.timedelta):
                    f.write('{},{}\n'.format(i, self.cost_time_info[i].total_seconds()))
                else:
                    f.write('{},{}\n'.format(i, 'error'))
        safe_print('INFO: cost time info write in {}!'.format(name))

    def run(self, process_num=1, run_time=1):
        logger = configs.LOGGER
        if process_num == 1 and sum([len(case) for case in self.task_set.values()]) == 1:
            logger.debug("The number of running processes is 1, which will run serial")
            self.serial_run_task()
        else:
            logger.debug(
                "The number of running processes is {}, and will run in parallel".format(
                    process_num
                )
            )
            self.parallel_run_task(process_num)
        print_type = configs.get_val("print_type")
        g_summary = self.gen_summary(print_type, run_time).splitlines()
        for line in g_summary:
            logger.info(line)
        pass_num = int(g_summary[-2].split(",")[2].replace(" PASS: ", "")) if "PASS" in g_summary[-2].split(",")[2] else int(g_summary[-2].split(",")[3].replace(" PASS: ", ""))
        failed_num = int(g_summary[-2].split(",")[3].replace(" FAIL: ", "")) if "FAIL" in g_summary[-2].split(",")[3] else int(g_summary[-2].split(",")[2].replace(" FAIL: ", ""))
        r = {
            "total": int(g_summary[-2].split(",")[1].replace(" total: ", "")),
            "pass": pass_num,
            "failed": failed_num
        }
        return self.result[FAIL], r

    def split(self, num):
        logger = configs.LOGGER
        for task_name in self.task_set:
            temp = sorted([str(i) for i in self.task_set[task_name] if i.result[0] != UNRESOLVED])
            for x in range(len(temp)):
                temp[x] = temp[x].replace('_' + task_name, '').split(os.sep, 1)[1]
            each_list = [[] for _ in range(num)]
            testlist_str = '[ALL-TEST-CASE]\n'
            for i in range(len(temp)):
                each_list[i % num].append(temp[i])
            for i in range(num):
                if each_list[i]:
                    if len(self.task_set) == 1:
                        name = os.path.join(str(self.path), 'testlist_{}'.format(i + 1))
                    else:
                        name = os.path.join(str(self.path), 'testlist_{}_{}'.format(task_name, i + 1))
                    temp_case_str = testlist_str + '\n'.join(each_list[i])
                    with open(name, 'w') as f:
                        f.write(temp_case_str)
                    logger.info('Test case part {} listed in {}'.format(i + 1, name))

    def gen_brief_summary(self, print_type):
        total = sum(self.result.values())
        result = copy.deepcopy(self.result)
        total -= result.pop(NOT_RUN)
        if UNRESOLVED not in print_type:
            total -= result.pop(UNRESOLVED)

        total_summary = "TestSuiteTask: {}, Total: {}, ".format(
            self.name, total
        ) + "".join(
            [
                "{}: {}, ".format(k, v)
                for k, v in sort_dict_items(result, index=1, reverse=True)
            ]
        )
        task_set_summary = ""
        for tasks_name in self.task_set:
            total = sum(self.task_set_result[tasks_name].values())
            task_result = copy.deepcopy(self.task_set_result[tasks_name])
            total -= task_result.pop(NOT_RUN)
            if UNRESOLVED not in print_type:
                total -= task_result.pop(UNRESOLVED)
            task_set_summary += (
                    "\n  "
                    + tasks_name
                    + ", total: {}, ".format(total)
                    + "".join(
                [
                    "{}: {}, ".format(k, v)
                    for k, v in sort_dict_items(task_result, index=1, reverse=True)
                ]
            )
            )
        return total_summary + task_set_summary + "\n"

    def gen_summary(self, print_type=None, run_time=1):
        self.result = defaultdict(int)
        for name in self.task_set_result:
            for status, num in self.task_set_result[name].items():
                self.result[status] += num
        if print_type is None:
            print_type = configs.get_val("print_type")
        brief_summary = self.gen_brief_summary(print_type)
        summary = "-" * 120
        summary += "\nTestSuite Path: {}\n".format(self.path)
        for tasks_name in self.task_set:
            for task in sorted(self.task_set[tasks_name], key=lambda task: task.name):
                result = task.result[0]
                if result in print_type or (not print_type and result in DEFAULT_PRINT):
                    if run_time == 1 or (run_time > 1 and result == FAIL):
                        summary += "  {}, Case: {}, Result: {}, LogFile: {}\n".format(
                            tasks_name, task.case_path, result, task.temp_dir + ".log"
                        )
        summary += "\n" + brief_summary
        summary += "-" * 120
        return summary

    def gen_result(self):
        from maple_test.test import Result
        print_type = configs.get_val("print_type")
        results = []
        for task_name in self.task_set:
            for task in self.task_set[task_name]:
                result = Result(
                    task.case_path,
                    self.cfg_path.parent.name,
                    task_name,
                    task.result[0],
                    task.commands,
                    task.result[1],
                    task.log_config,
                )
                if len(print_type) != 0 and task.result[0] == print_type[0]:
                    results.append(result)
                if len(print_type) == 0:
                    results.append(result)
        return results

    def gen_xml_result(self, root):
        from xml.etree import ElementTree

        suite = ElementTree.SubElement(
            root,
            "testsuite",
            failures=str(self.result[FAIL]),
            tests=str(sum(self.result.values())),
            name="{} {}".format(self.name, self.path),
        )
        for result in sorted(self.gen_result()):
            result.gen_xml(suite)
        return suite

    def gen_json_result(self):
        json_result = OrderedDict()
        json_result["name"] = "{} {}".format(self.name, self.path)
        json_result["total"] = sum(self.result.values())
        for status in self.result:
            if status == NOT_RUN:
                continue
            json_result[status] = self.result[status]
        json_result["tests"] = []
        for result in sorted(self.gen_result()):
            json_result["tests"].append(result.gen_json_result())
        return json_result


class SingleTask:
    def __init__(self, case, config, running_config, condition):
        self.name = "{}{}{}".format(case.test_name, OS_SEP, case.name)
        self.path = Path(self.name)
        self.condition = condition
        config = config.get_case_config(case)
        ensure_config_initialized()
        base_path = Path(__file__).resolve().parent.parent.parent / "testsuites"
        global OVERWRITE_FILE
        if running_config["directory_structure"] == "normal":
            self.temp_dir = "{}_{}".format(self.path.name.replace(".", "_"), int(time.time()))
        elif running_config["directory_structure"] == "tile":
            self.temp_dir = "{}_{}".format(self.path.name.replace(".", "_"), str(uuid.uuid1()).replace("-", ""))
        if not configs.get_val("compatible") and running_config.get("directory_list"):
            file_mod = "w" if OVERWRITE_FILE else "a"
            with open(str(running_config["directory_list"]), file_mod) as f:
                f.write("{} {}".format(case.path.relative_to(base_path), self.temp_dir) + "\n")
            if OVERWRITE_FILE:
                OVERWRITE_FILE = False
        elif configs.get_val("compatible") and running_config.get("directory_list"):
            for k, v in directory_dict.items():
                if not os.path.exists(os.path.join(base_path, k)):
                    continue
                if os.path.samefile(os.path.join(base_path, k), case.path):
                    self.temp_dir = v
                    break
        if running_config["directory_structure"] == "normal":
            self.work_dir = running_config["temp_dir"] / self.path.parent / self.temp_dir
            self.log_config = "{}_{}".format(self.name.replace(".", "_"), self.temp_dir.split("_")[-1])
        elif running_config["directory_structure"] == "tile":
            self.work_dir = running_config["temp_dir"] / self.temp_dir
            self.log_config = self.temp_dir
        timeout = running_config["timeout"]
        if case.timeout:
            timeout = case.timeout
        self.running_config = {
            "case_path": case.path,
            "work_dir": self.work_dir,
            "log_config": (running_config["log_config"], self.log_config),
            "timeout": timeout,
            "env": config["env"]
        }
        self.case_path = case.relative_path
        if case.commands:
            if configs.get_val("compatible") and running_config.get("directory_list"):
                prepare_result = (NOT_RUN, None)
            else:
                prepare_result = self.prepare(case, self.work_dir, config)
            self.result = (NOT_RUN, None)
            log_dir = (running_config.get("log_config").get("dir") / self.log_config).parent
            self.prepare_dir(log_dir)
            self.result = prepare_result
        else:
            self.result = (UNRESOLVED, (1, "", "No valid command statement was found."))

        self.commands = []
        if self.result[0] == NOT_RUN:
            self._form_commands(case, config)

        self.check_and_record_cases_without_level(case.path, base_path)

    def prepare(self, case, dest, config):
        src_path = case.path
        logger = configs.LOGGER
        if not src_path.exists():
            err = "Source: {} is not existing.\n".format(src_path)
            logger.debug(err)
            return FAIL, err
        self.prepare_dir(dest)
        shutil.copy(str(src_path), str(dest))
        return self.prepare_dependence(src_path.parent, case.dependence, case.separation_by_files, dest, config)


    @staticmethod
    def separate_by_files(separation, dest, logger, config):
        if separation == []:
            return
        
        for filepath, content in separation:
            filepath = SingleTask._form_line(filepath, config)
            path = os.path.normpath(dest / filepath)
            (dir, file) = os.path.split(path)
            SingleTask.prepare_dir(Path(dir))
            with open(path, "w") as file:
                file.write(content)


    @staticmethod
    def check_and_record_cases_without_level(case_path, base_path, output_file='cases_without_level.txt'):
        global OVERWRITE_LEVEL_FILE
        has_level = False
        has_exec = False

        try:
            with open(case_path, 'r', encoding='utf-8') as file:
                for line in file:
                    if line.strip().startswith('// LEVEL'):
                        has_level = True
                    if line.strip().startswith('// EXEC'):
                        has_exec = True
                    if has_level and has_exec:
                        break
        except IOError as e:
            print(f"无法读取文件 {case_path}: {e}")
            return

        file_mod = "w" if OVERWRITE_LEVEL_FILE else "a"
        if OVERWRITE_LEVEL_FILE:
            OVERWRITE_LEVEL_FILE = False
        if not has_level and has_exec:
            try:
                with open(output_file, file_mod, encoding='utf-8') as out_file:
                    try:
                        rel_path = case_path.relative_to(base_path)
                    except ValueError:
                        rel_path = case_path
                    out_file.write(str(rel_path) + '\n')
            except IOError as e:
                print(f"无法写入输出文件 {output_file}: {e}")

    @staticmethod
    def prepare_dependence(src_dir, dependence, separation_by_files, dest, config):
        logger = configs.LOGGER
        src_files = []
        for file in dependence:
            file = SingleTask._form_line(file, config)
            src_path = src_dir / file
            if src_path.exists():
                src_files.append(src_path)
            else:
                err = "DEPENDENCE keyword error, file: {} NotFound".format(file)
                logger.debug(err)
                return FAIL, err
        src_files = set(src_files)
        for file in src_files:
            if file.is_file():
                shutil.copy(str(file), str(dest))
            else:
                name = file.name
                try:
                    shutil.copytree(str(file), str(dest / name))
                except:
                    pass
        SingleTask.separate_by_files(separation_by_files, dest, logger, config)
        return NOT_RUN, None

    @staticmethod
    def prepare_dir(directory):
        logger = configs.LOGGER
        if not directory.exists():
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except FileExistsError as err:
                logger.debug(err)
                logger.debug(
                    "File: {} is not an existing non-directory file.".format(directory)
                )

    def _form_commands(self, case, config):
        for command_info in case.commands:
            command = command_info['cmd']
            compare_cmd = " {} {} --comment={} ".format(
                EXECUTABLE, COMPARE, quote(case.comment)
            )
            if configs.get_val('transfer'):
                compare_cmd += " --transfer {} ".format(case.path)
            if self.condition:
                def format_condition(x: set):
                    return str(x).replace('{', '"').replace('}', '"')

                compare_cmd += " --condition={} ".format(format_condition(self.condition))

            # no pipe cmd.
            if not command_info[PIPE_KEY]:
                command = self._form_line(command, config)
                command_info['cmd'] = format_compare_command(command, compare_cmd)
                self.commands.append(command_info)
            # split one cmd into two.
            else:
                command_a = self._form_line(command[0], config)
                command_b = self._form_line(command[1], config)
                command_info['cmd'] = format_compare_command(command_a, compare_cmd)
                self.commands.append(command_info)
                temp = {}
                temp.setdefault('cmd', format_compare_command(command_b, compare_cmd))
                temp.setdefault(PIPE_KEY, False)
                temp.setdefault(EXIT_CODE, 0)
                self.commands.append(temp)

    @staticmethod
    def _form_line(line, config):
        for key, value in config.get("internal_var").items():
            end = 0
            while end < len(line):
                start = line.find("%{}".format(key), end)
                if start == -1:
                    break
                end = len(key) + start + 1
                if end == len(line):
                    line = line[:start] + value + line[end:]
                elif not line[end].isalnum() and line[end] != "_":
                    line = line[:start] + value + line[end:]
                end = len(value) + start + 1
        return line

    def __repr__(self):
        return "{}".format(self.path)


def format_compare_command(raw_command, compare_cmd):
    end = 0
    while end < len(raw_command):
        start = raw_command.find("compare ", end)
        if start == -1:
            break
        end = start + len("compare ")
        if start == 0:
            prev_char = ""
        else:
            prev_char = raw_command[start - 1]
        if not prev_char.isalnum() and prev_char != "_":
            raw_command = raw_command[:start] + compare_cmd + raw_command[end:]
    return raw_command


def sort_dict_items(d, index=0, reverse=False):
    return sorted(d.items(), key=lambda item: item[index], reverse=reverse)
