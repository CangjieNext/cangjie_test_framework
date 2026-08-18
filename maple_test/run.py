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
import os
import re
import signal
import subprocess
import sys
import stat
import time
import timeit
import logging
import platform
import ctypes
import shutil
import datetime
from textwrap import indent

from maple_test import configs
from maple_test.configs import construct_logger
from maple_test.utils import PASS, FAIL, PIPE_KEY, EXIT_CODE, ENCODING, PRINT_LOCK
from maple_test.utils import add_run_path, process_exit_code, safe_print

is_initialized = False


def ensure_config_initialized():
    global is_initialized
    if not is_initialized:
        _, _, _ = configs.init_config()
        is_initialized = True


class TestError(Exception):
    pass


def handle_result_encoding(com_out, com_err, logger):
    try:
        com_out = com_out.decode(ENCODING, errors="strict")
    except UnicodeDecodeError:
        try:
            com_out = com_out.decode('utf-8', errors="strict")
        except UnicodeDecodeError:
            com_out = com_out.decode('utf-8', errors="ignore")
            logger.debug("Can not decode stdout with {}, ignore error!".format(ENCODING))
    try:
        com_err = com_err.decode(ENCODING, errors="strict")
    except UnicodeDecodeError:
        try:
            com_err = com_err.decode('utf-8', errors="strict")
        except UnicodeDecodeError:
            com_err = com_err.decode('utf-8', errors="ignore")
            logger.debug("Can not decode stderr with {}, ignore error!".format(ENCODING))
    return com_out, com_err


def run_command_win(cmd, work_dir, timeout, logger, env=None, mystdin=None):
    """Run commands using subprocess on Windows.

    We set PYTHONIOENCODING to utf-8 on Windows to keep up with
    test case file`s read encoding in compare.py to avoid some
    character set issues.

    """
    new_env = add_run_path(str(work_dir))
    new_env.update(env)
    encoding_env = {'PYTHONIOENCODING': 'utf-8'}
    new_env.update(encoding_env)
    buffer_env = {'PYTHONUNBUFFERED': '1'}  # disable buffer in the subprocess
    new_env.update(buffer_env)
    process_command = subprocess.Popen(
        cmd,
        shell=True,
        cwd=str(work_dir),
        env=new_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        bufsize=0
    )
    logger.debug("execute cmd ===>>>: %s", cmd)
    return_code = com_out = com_err = None
    try:
        com_out, com_err = process_command.communicate(input=mystdin, timeout=timeout)
    except subprocess.CalledProcessError as err:
        return_code, com_out, com_err = err.returncode, "", err
        logger.exception(err)
        return return_code, com_out, com_err
    except subprocess.TimeoutExpired:
        os.system('taskkill /t /f /pid {}'.format(process_command.pid))
        return_code, com_out, com_err = 3, "TimeOut", "TimeOut"
        return return_code, com_out, com_err
    else:
        return_code = process_command.returncode
        com_out, com_err = handle_result_encoding(com_out, com_err, logger)
        return return_code, com_out, com_err
    finally:
        handle = ctypes.windll.kernel32.OpenProcess(1, False, process_command.pid)
        ctypes.windll.kernel32.TerminateProcess(handle, -1)
        ctypes.windll.kernel32.CloseHandle(handle)
        logger.debug("return code: %d", return_code)
        # For some cases that have a large amount of stdout, windows may get OOM if this code is on
        logger.debug("stdout : \n%s",
                    indent(com_out, "+\t", lambda line: True).encode().decode(ENCODING, errors='ignore'))
        logger.debug("stderr : \n%s",
                     indent(com_err, "@\t", lambda line: True).encode().decode(ENCODING, errors='ignore'))


def run_command_linux(cmd, work_dir, timeout, logger, env=None, mystdin=None):
    """Run commands using subprocess on Linux"""
    new_env = add_run_path(str(work_dir))
    new_env.update(env)
    buffer_env = {'PYTHONUNBUFFERED': '1'}
    new_env.update(buffer_env)
    process_command = subprocess.Popen(
        cmd,  # disable buffer in the subprocess
        shell=True,
        cwd=str(work_dir),
        env=new_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        start_new_session=True,
        bufsize=0,
        stdin=subprocess.PIPE,
        executable='/bin/bash'
    )
    logger.debug("execute cmd ===>>>: %s", cmd)
    return_code = com_out = com_err = None
    try:
        com_out, com_err = process_command.communicate(input=mystdin, timeout=timeout)
    except subprocess.CalledProcessError as err:
        return_code, com_out, com_err = err.returncode, "", err
        logger.exception(err)
        return return_code, com_out, com_err
    except subprocess.TimeoutExpired:
        return_code, com_out, com_err = 3, "", "TimeOut"
        return return_code, com_out, com_err
    else:
        return_code = process_command.returncode
        com_out, com_err = handle_result_encoding(com_out, com_err, logger)
        return return_code, com_out, com_err
    finally:
        process_command.kill()
        try:
            os.killpg(process_command.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        logger.debug("return code: %d", return_code)
        logger.debug("stdout : \n%s",
                     indent(com_out, "+\t", lambda line: True).encode().decode(ENCODING, errors='ignore'))
        logger.debug("stderr : \n%s",
                     indent(com_err, "@\t", lambda line: True).encode().decode(ENCODING, errors='ignore'))


def run_commands(
        position, old_result, commands, case_path, work_dir, timeout, log_config, env=None,
        run_script_prefix=None
):
    name = log_config[1]
    log_file = str(log_config[0].get("dir") / name) + '.log'
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    logger = construct_logger(log_config[0], log_config[1], file_fmt=formatter)
    logger.debug("Case Path: {}".format(case_path))
    if not commands:
        logger.error("Run task exit unexpected : {}".format(old_result[1]))
        return position, old_result
    remain_time = timeout
    result = [PASS, None]
    logger.debug("Work directory: {}".format(work_dir))

    if platform.system() == "Windows":
        run_command = run_command_win
    else:
        run_command = run_command_linux

    commands_result = []
    mystdin = None
    start_time = datetime.datetime.now()
    cjc_num = 0
    coverage = True
    for index, command in enumerate(commands):
        # handle EXEC-PIPE
        if index > 0 and commands[index - 1][PIPE_KEY]:
            last_stdout = commands_result[index - 1]['stdout']
            # ignore unicode encode error
            mystdin = bytes(last_stdout, ENCODING, errors='ignore')

        if platform.system() == "Windows":
            cmd_list = command['cmd'].split()
            for idx in range(len(cmd_list)):
                cmd_list[idx] = re.sub(r"^\./", r".\\", cmd_list[idx], count=1)
                # limit character of windows path: < > " \ | ? http:// https:// ftp:// ssh://
                # matched cases: temp/abc/d.cj, temp/abc//d.cj, temp/abc/*.cj
                # matched cases: .\temp/abc/d.cj, .\\temp/abc//d.cj, .\temp/abc/*.cj
                # not matched cases: //ASSERT , --comment="//"
                if re.match(r'^(?!https?://|ftp://|ssh://)(\w|\.(\\)+)([^<>"\\|?]*/[^<>:"\\|?]*)+$', cmd_list[idx]):
                    cmd_list[idx] = cmd_list[idx].replace("/", "\\")
            command['cmd'] = " ".join(cmd_list)
        start = timeit.default_timer()
        origin_return_code, com_out, com_err = run_command(
            command['cmd'], work_dir, remain_time, logger, env, mystdin
        )
        return_code = process_exit_code(origin_return_code)
        run_time = timeit.default_timer() - start
        remain_time = remain_time - run_time
        logger.debug(
            "Run time: {:.5} second, remain time: {:.5} second".format(run_time, remain_time)
        )
        command_result = {}
        command_result["cmd"] = command['cmd']
        command_result["return_code"] = return_code
        command_result["stdout"] = com_out
        command_result["stderr"] = com_err
        commands_result.append(command_result)
        return_code_white_list = command[EXIT_CODE]
        if return_code == return_code_white_list:
            result = [PASS, commands_result]
        else:
            result = [FAIL, commands_result]
            logger.error("Failed!")
            logger.error("Command return code {} not equals to expected return code {}".format(origin_return_code, return_code_white_list))
            break
    result.append(datetime.datetime.now() - start_time)
    if result[0] == PASS:
        logger.debug("Task executed successfully")
    handlers = logger.handlers[:]
    for handler in handlers:
        handler.close()
        logger.removeHandler(handler)
    ensure_config_initialized()
    if result[0] == PASS and not configs.get_val('keep_temp'):
        # Cross-device test drivers (e.g. the Android run_cross_compilation.py
        # script) cannot tell which RUN-EXEC invocation is the last one of a
        # case, so a passing case leaves its remote run directory behind on
        # small-capacity devices. The framework owns the "case finished"
        # signal, so it re-invokes the same script with --cleanup here to
        # remove that directory. The script derives the remote path from the
        # basename of the work directory it runs in, so this must happen
        # before the local work_dir is removed.
        if run_script_prefix:
            cleanup_cmd = '{} --cleanup'.format(run_script_prefix)
            cleanup_timeout = min(timeout, 60) if timeout else 60
            # The script's --cleanup path removes the remote case dir. Its exit
            # code is 0 on a clean rm, non-zero if the rm failed (the script
            # updates EXIT_CODE on a remove-stage failure) or if argparse
            # rejected --cleanup (old script without the flag — exit 2). Either
            # way the device may be left with a stale run dir, so surface it:
            # the old logger.debug here was invisible by default (stream level
            # is WARNING) and leftover remote dirs went unnoticed. run_command
            # is bound to run_command_win/linux above for the command loop.
            try:
                origin_rc, com_out, com_err = run_command(
                    cleanup_cmd, work_dir, cleanup_timeout, logger, env, None,
                )
            except Exception as e:
                logger.warning(
                    "Remote cleanup aborted for %s: %s", work_dir, e,
                )
            else:
                rc = process_exit_code(origin_rc)
                if rc != 0:
                    logger.warning(
                        "Remote cleanup FAILED for %s (exit %s): %s",
                        work_dir, origin_rc, (com_err or com_out or "").strip()[:500],
                    )
        try:
            def change_mod_write(func, path, info):
                os.chmod(path, stat.S_IWRITE)
                func(path)

            shutil.rmtree(work_dir, onerror=change_mod_write)
        except Exception as e:
            safe_print("Remove {} failed, maybe remove it manually, {}".format(work_dir, e))
    return position, result


def progress(results, progress_type):
    """Output test progress"""

    if progress_type == "silent":
        return 0
    if progress_type == "normal":
        time_gape = 1
        print_progress = sys.stdout.write
    else:
        time_gape = 10
        print_progress = print
    finished = 0
    total = len(results)
    while total != finished:
        time.sleep(time_gape)
        finished = sum([result.ready() for result in results])
        rate = finished / total
        print_progress(
            "\rRunning test cases: {:.2%} ({}/{}) ".format(rate, finished, total)
        )
        flush_stdout()


def flush_stdout():
    max_retries = 3
    retries = 0
    while retries < max_retries:
        try:
            with PRINT_LOCK:
                sys.stdout.flush()
            break  # 如果成功执行 sys.stdout.flush()，则跳出循环
        except BlockingIOError:
            safe_print("Caught BlockingIOError, retrying...")
            retries += 1
            time.sleep(1)  # 可以添加一些延迟，避免过于频繁重试
    else:
        safe_print("Failed to flush stdout after {} retries".format(max_retries))

