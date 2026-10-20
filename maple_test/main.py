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
"""
maple test - Maple Tester


"""
import os.path
import shutil
import time
import io
import sys

sys.output = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')
KeepRunFile = False
from xml.etree import ElementTree

from maple_test import configs
from maple_test.task import TestSuiteTask
from maple_test.run import TestError, KeyboardInterrupted, request_stop


def main():
    test_suite_config, running_config, log_config = configs.init_config()
    logger = configs.LOGGER

    test_paths = test_suite_config.get("test_paths")
    cli_test_cfg = test_suite_config.get("test_cfg")
    cli_running_config = test_suite_config.get("cli_running_config")

    root = ElementTree.Element("testsuites")
    json_result = []

    retry = configs.get_val("retry")
    pass_rate = configs.get_val("pass_rate")
    result = ""
    failed = False
    failed_rate = False
    split_num = configs.get_val("split_num")
    check = configs.get_val("check")
    condition = configs.get_val("condition")
    level = configs.get_val("level")
    xml_output = configs.get_val("xml_output")
    json_output = configs.get_val("json_output")

    repeat = configs.get_val("repeat") or 1
    if repeat > 1 and (configs.get_val("compatible") or split_num):
        # --compatible reuses work dirs recorded in a directory_list (the
        # repeat tag would be dropped and repeats would collide on one dir),
        # and --split writes task names into split testlists (the tag would
        # end up in the generated lists where no such case file exists).
        sys.exit("[ERROR] --repeat cannot be used together with --compatible or --split")

    try:
        test_interrupted = False
        for test in test_paths:
            test_cfg = cli_test_cfg
            test_result = None
            test_failed = False
            test_failed_rate = False
            loop_interrupted = False
            if test.exists():
                if not test_cfg:
                    test_cfg = test / "test.cfg"
                try:
                    task = TestSuiteTask(test, test_cfg, running_config, condition, level, cli_running_config)
                except TestError as e:
                    logger.info(e)
                    continue
                if not task.task_set:
                    continue
                if split_num:
                    task.split(split_num)  # only split, not run.
                elif check:
                    task.check(check)
                else:
                    for run_time in range(1, retry + 2):
                        logger.info("Run {} times".format(run_time))
                        try:
                            failed_num, num_dict = task.run(configs.get_val("processes"), run_time)
                        except (KeyboardInterrupted, KeyboardInterrupt):
                            # Interrupted by the user (graceful stop, or a
                            # second Ctrl+C that abandoned the pool): keep
                            # the results of the cases that finished (the
                            # rest are NOT_RUN) and generate the usual
                            # result files. A test_result left over from an
                            # earlier retry round is stale here — regenerate
                            # it from the current (partial) results, and do
                            # not skip the xml/json output the normal path
                            # produces.
                            test_interrupted = True
                            loop_interrupted = True
                            test_result = task.gen_summary([])
                            result += test_result
                            if xml_output:
                                task.gen_xml_result(root)
                            if json_output:
                                json_result.append(task.gen_json_result())
                            break
                        if num_dict["total"] != 0 and num_dict["pass"] / num_dict["total"] * 100 >= pass_rate:
                            test_failed_rate = False
                        else:
                            test_failed_rate = True
                        if failed_num > 0:
                            test_failed = True
                        else:
                            test_failed = False
                        test_result = task.gen_summary([])
                    failed |= test_failed
                    failed_rate |= test_failed_rate
                    result += test_result if test_result else task.gen_summary([])
                    if xml_output:
                        task.gen_xml_result(root)
                    if json_output:
                        json_result.append(task.gen_json_result())
                if loop_interrupted:
                    # An interrupted run also stops any later test paths.
                    break

            else:
                logger.info("Test path: {} does not exist, please check".format(test))

        if xml_output:
            with xml_output.open("w") as f:
                f.write(ElementTree.tostring(root).decode("utf-8"))

        if json_output:
            with json_output.open("w") as f:
                import json

                json.dump(json_result, f, indent=2)

        output = configs.get_val("output")
        if output:
            if output.exists() and output.is_file():
                name = "{}_{}{}".format(output.stem, int(time.time()), output.suffix)
                logger.info(
                    "result file: {} exists, will move exists file to: {}".format(
                        output, name
                    )
                )
                shutil.move(str(output), str(output.parent / name))
            logger.info("Save test result at: {}".format(output))
            with output.open("w", encoding="utf-8") as f:
                f.write(result)
        if test_interrupted:
            logger.info("Run interrupted by user; partial results saved.")
    finally:
        request_stop()
        temp_dir = running_config.get("temp_dir")
        if configs.get_val('debug') or configs.get_val('keep_temp'):
            logger.debug("Keep temp file at %s", temp_dir)
        elif temp_dir.exists():
            logger.debug("remove temp_dir %s", temp_dir)
            try:
                shutil.rmtree(str(temp_dir))
            except OSError as e:
                # After an interrupt a worker may still hold a case dir
                # briefly; the cleanup must not crash the run.
                logger.debug("remove temp_dir failed: {}".format(e))

        if "CHECK_LEVEL" in os.environ:
            if os.path.exists("cases_without_level.txt") and os.path.getsize("cases_without_level.txt") != 0:
                with open("cases_without_level.txt", "r", encoding='utf-8') as file:
                    content = file.read().strip()
                    print("These cases do not have level: \n")
                    print(content)
                    print("-" * 120)

        if configs.get_val("fail_exit") and failed:
            exit(1)

        if configs.get_val("pass_rate") and failed_rate:
            exit(1)


if __name__ == "__main__":
    main()
