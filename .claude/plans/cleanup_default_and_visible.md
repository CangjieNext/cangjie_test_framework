# 让跨端用例临时目录清理成为默认且可见

## 背景：现状与真正的问题

用户反馈 android/ohos 用例执行后，远端临时目录(`/data/local/tmp/run/<work_dir>` 或 RTOS 的 `/tmp/run/<work_dir>`)及里面的二进制中间产物仍然残留。

用户诊断"cfg 调用时没加 `--cleanup`"，但实际核查代码后发现：**清理机制已经提交存在，只是失败了被静默吞掉**：

1. `cangjie_test_framework/maple_test/run.py:248-264`(已提交到 `bug_fix_0728`/HEAD `d40aaf8`)：用例 `PASS and not keep_temp` 时，构造 `cleanup_cmd = run_script_prefix + ' --cleanup'`，用 `run_command_win/linux` 跑一次。
2. `cangjie_test_framework/maple_test/task.py:655,677-698`(已提交)：`run_script_prefix` 由 `_resolved_run_script_prefix` 生成——截掉 `| ignore_cmd_redirect` 尾巴、`_form_line` 展开 `%key` 内部变量、保留 `$ENV`/`${ENV}` 给宿主 shell。
3. `testsuites/HLT/configs/cjnative/run_cross_compilation.py`(cangjie_test 仓，工作区已改未提交)：`parse_cli()` 已加 `--cleanup` flag(`action="store_true"`)，`execute_cmd` 已改 `ZERO_OR_MORE`，`main()` 已有 cleanup 分支(`:465-470` 走 `rm -rf {remote_root}/{remote_path}` 后 return)。

所以架构是对的、默认就是清理(除非 `--keep_temp`)。**真正失败在两个静默点**：

- **静默点 A(框架侧)** `run.py:262-264`：`run_command` 的返回值 `(return_code, com_out, com_err)` 被丢弃，且 `except` 只捕获 Python 异常(timeout/subprocess 崩溃)。脚本 `--cleanup` 若因 argparse 报错(exit 2)或 `rm` 失败(exit 0，见下)，框架完全看不到，只打 `logger.debug`，默认不可见(stream level=WARNING)。
- **静默点 B(脚本侧)** `run_cross_compilation.py:374-407` 的 `run_cmd`：对 `stage == "remove_file_on_remote"`，`return_code != 0` 时不抛异常(`:403` 条件排除了 remove 阶段)，`EXIT_CODE` 也不更新(`:401-402`)。于是 `rm` 失败→脚本仍 `return`(exit 0)→框架以为成功。

结论：用户看到的"目录残留"= 静默失败。修复目标是**让清理失败可见，并让脚本默认就清理、`--keep_temp` 才保留**，与用户要求一致。

## 关键约束(必须遵守)

- **脚本被逐条 RUN-EXEC 调用，无法知道哪条是最后一条**。所以脚本不能在"正常执行结束"时自清理——会删掉同 case 后续命令还需复用的设备目录(如 `dynamic_link_openssl.cj` 有 `RUN-EXEC-PIPE` + `EXEC: %check-dylib-dep` 两条命令复用同一目录)。
- 因此"case 结束信号"必须由框架持有：框架在 case PASS 后**只调一次** `--cleanup`。这是现状，**保留不动**。
- 用户的"--cleanup 作为默认，除非 --keep_temp"= 框架默认就调 `--cleanup`、脚本默认就执行 rm。现状已满足此语义；修复只是让它**真正生效且失败可见**。

## 改动清单

### 改动 1：脚本侧让 `--cleanup` 失败可见且默认执行
**文件**：`E:\cangjie_test_suite\cangjie_test\testsuites\HLT\configs\cjnative\run_cross_compilation.py`

1. **`parse_cli()` 新增 `--keep-temp`**(与框架 `--keep_temp` 名字对应，argparse 用连字符)：
   ```python
   parser.add_argument(
       "--keep-temp", action="store_true", default=False, dest="keep_temp",
       help="keep the remote case dir after the case finishes (mirror of the "
            "framework's --keep_temp). When set, --cleanup is a no-op.",
   )
   ```
   - `dest="keep_temp"` 保持点号访问一致。

2. **`main()` cleanup 分支尊重 `--keep-temp`**(`:465-470` 改写)：
   ```python
   if opts.cleanup:
       if opts.keep_temp:
           # Framework asked us to keep temp; honor it even in cleanup mode.
           return
       remove_cmd = "rm -rf {}/{}".format(remote_root.rstrip('/'), remote_path)
       cleanup_cmd = construct_tool_shell_cmd(remove_cmd)
       cleanup_timeout = timeout if timeout else 60
       run_cmd("remove_file_on_remote", cleanup_cmd, ".", cleanup_timeout)
       # run_cmd already raises on non-zero for remove? NO — see改动 3.
       return
   ```
   - 保留 `--cleanup` 为"显式清理模式"(框架在 PASS 后调它)。脚本**不在正常执行路径自清理**(约束)。

3. **`run_cmd()` 让 remove 阶段失败可见**(`:401-407`)：
   现状 remove 阶段 `return_code != 0` 不抛、不更新 `EXIT_CODE`。改为：remove 阶段失败时记 `logging.error` 并让 `EXIT_CODE` 反映它(但不抛异常——cleanup 失败不应让已 PASS 的 case 变 FAIL，框架侧改用 warning 汇报)：
   ```python
   global EXIT_CODE
   if stage != "remove_file_on_remote":
       EXIT_CODE = int(return_code)
   else:
       # remove is best-effort: a non-zero here means the remote dir may
       # still exist, but it must NOT flip an already-passing case to FAIL.
       # Surface it via EXIT_CODE so the framework's cleanup call can see
       # a non-zero and log a visible warning.
       if return_code != "0":
           EXIT_CODE = int(return_code) if str(return_code).isdigit() else 1
           logging.error("cleanup/remove stage failed (exit %s): %s", return_code, com_err)
   if return_code != "0" and stage != "remove_file_on_remote":
       raise RunError(...)   # 原逻辑不动
   ```

   等价地、更简洁：remove 阶段失败时更新 `EXIT_CODE` + `logging.error`，不 raise。

4. **`main()` 末尾 `sys.exit` 反映清理结果**(`:499-508`)：现状已 `sys.exit(EXIT_CODE if EXIT_CODE != 0 else 1)`(RunError 时)。正常 cleanup 路径走 `return` 后落到 `if __name__` 的 try 外，exit 0。若 cleanup 失败 `EXIT_CODE != 0`，需在 `return` 前 `sys.exit(EXIT_CODE)`。故 cleanup 分支改为：
   ```python
       run_cmd("remove_file_on_remote", cleanup_cmd, ".", cleanup_timeout)
       sys.exit(EXIT_CODE)   # 0=cleaned ok, non-zero=rm failed (visible to framework)
       return  # unreachable, kept for clarity
   ```

### 改动 2：框架侧让清理失败可见 + 传 keep_temp
**文件**：`E:\cangjie_test_suite\cangjie_test_framework\maple_test\run.py`(`:257-264`)

```python
if run_script_prefix:
    cleanup_cmd = '{} --cleanup'.format(run_script_prefix)
    cleanup_timeout = min(timeout, 60) if timeout else 60
    # run_command already gated by `not keep_temp` at line 248; the script
    # also honors --keep-temp below, so we don't pass it here redundantly.
    run_command = run_command_win if platform.system() == "Windows" else run_command_linux
    origin_rc, com_out, com_err = run_command(
        cleanup_cmd, work_dir, cleanup_timeout, logger, env, None,
    )
    rc = process_exit_code(origin_rc)
    if rc != 0:
        # Was: logger.debug("Remote cleanup skipped ...") — invisible by default.
        # Now surface it so a silently-failing rm (the root cause of leftover
        # remote dirs) shows up in the console + per-case log.
        logger.warning(
            "Remote cleanup FAILED for %s (exit %s): %s",
            work_dir, origin_rc, (com_err or com_out or "").strip()[:500],
        )
```

- 去掉外层 `try/except`(subprocess 级异常如 timeout 仍由 `run_command_win/linux` 内部转成 `(3, "TimeOut", "TimeOut")` 返回，不会抛到这层)。若担心极端 subprocess 异常，保留一个 `except Exception` 兜底记 `warning` 即可，但不再吞为 debug。
- `process_exit_code` 已 `from maple_test.utils import ... process_exit_code`(run.py:35 已导入)。

### 改动 3(可选，兜底)：框架把 `KEEP_TEMP` 注入子进程 env
若希望脚本即使在未被框架 `--cleanup` 显式调用的路径下也能感知 `keep_temp`，可在 `run_commands` 里给 cleanup 调用的 env 注入：
```python
cleanup_env = dict(env) if env else {}
cleanup_env["KEEP_TEMP"] = "1" if configs.get_val('keep_temp') else "0"
```
但当前 cleanup 只在 `not keep_temp` 时调用(248 行外层已挡)，所以 `KEEP_TEMP` 恒为 "0"，注入意义不大。**本改动可不做**，改动 1 的 `--keep-temp` 仅作脚本独立运行时的自洽选项。若用户要"脚本独立跑也默认清理、除非 `--keep_temp`"，再启用。

## 数据流(修复后)

```
case PASS + not keep_temp (run.py:248)
  → run_command(run_script_prefix + " --cleanup", work_dir, 60s)  [改动2]
  → 子进程: python run_cross_compilation.py --tool=adb --device=$DEVICE_ID --cleanup
  → 脚本 main():465 opts.cleanup=True, opts.keep_temp=False
  → rm -rf /data/local/tmp/run/<work_dir_basename>  (construct_tool_shell_cmd)
  → run_cmd("remove_file_on_remote", ...)  [改动1.3: rm 失败→EXIT_CODE!=0 + logging.error]
  → sys.exit(EXIT_CODE)  [改动1.4]
  → 框架 run.py 拿到 return_code, rc!=0 → logger.warning(...)  [改动2: 可见!]
  → shutil.rmtree(work_dir)  (本地照常删)
case PASS + keep_temp → run.py:248 False，整段跳过，本地+远端都保留(语义一致)
case FAIL → 脚本 run_case 异常分支自清(run_cross_compilation.py:359-371，不动)；框架不进 PASS 分支
```

## 验证清单

1. android case PASS 后：`hdc shell ls /data/local/tmp/run/<work_dir>` → No such file。
2. ohos case PASS 后：同上(hdc)。
3. rtos case PASS 后：`ssh ... ls /tmp/run/<work_dir>` → No such file。
4. 故意拔掉设备/改坏 `--device`：框架 console 应出现 `WARNING ... Remote cleanup FAILED for <work_dir> (exit <n>): <err>`，不再是静默 debug。
5. `--keep_temp`：本地 work_dir 与远端目录都保留。
6. 多 RUN-EXEC 的 case(如 `dynamic_link_openssl.cj`)：首条命令后设备目录仍在(脚本不自清)，case PASS 后框架只清一次——后续命令不受影响。
7. case FAIL：脚本异常分支自清(行为不变)，框架不重复清。

## 影响面

- **普通本地套**(无 `[run] script`)：`run_script_prefix=None`，cleanup 段跳过，零影响。
- **配 script 的旧脚本**(无 `--cleanup`/`--keep-temp`)：argparse 对 `--cleanup` 报错 exit 2 → 框架 `run.py` 改动 2 会 `warning` 报出来(而非静默)。**不再沉默**，用户能发现"脚本版本不对"。升级脚本即生效。
- 失败 case 行为不变。
