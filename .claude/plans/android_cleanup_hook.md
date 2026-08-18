# Android 设备文件 case 结束清理钩子

## 问题
`run_cross_compilation.py` 通过 cfg 的 `[run] script` 被框架逐条命令调用。脚本成功路径故意跳过 `remove_file_on_remote`(`run_cross_compilation.py:252-253`),因为同一 case 的后续 RUN-EXEC 命令需复用设备目录。但脚本无法感知"本 case 所有命令已跑完",导致成功 case 在设备上残留 `/data/local/tmp/run/<work_dir>` 目录,累积占用 Android 设备容量。

框架拥有"case 成功结束"的精确信号(`run.py:247` `result[0] == PASS`),但目前只删本地 work_dir(`run.py:253`),不感知设备。

## 方案:框架加 case 结束钩子 + 脚本加 cleanup 子命令

### 改动 1:脚本 `run_cross_compilation.py` 增加 `--cleanup` 模式

在 `parse_cli()`(`:205`):
- 增加 `--cleanup` flag(`action="store_true"`)。
- `execute_cmd` 位置参数从 `nargs=argparse.ONE_OR_MORE` 改为 `nargs='*'`,使 cleanup 调用无需传命令。

在 `main()`(`:310`)开头:
```python
if opts.cleanup:
    remote_path = os.path.basename(os.getcwd())
    remove_cmd = construct_tool_shell_cmd("rm -rf /data/local/tmp/run/" + remote_path)
    run_cmd("remove_file_on_remote", remove_cmd, ".", opts.timeout)
    sys.exit(EXIT_CODE)
```
- 设备目录名 = `os.path.basename(os.getcwd())`,与正常执行路径(`:335`)完全一致,因为框架在 case 的 work_dir 下调用脚本。
- 复用现有 `construct_tool_shell_cmd`、`run_cmd`、`run`、`tool`(已由 `--tool`/`--device` 设定)。`tool`/`device` 参数框架会照常传(cleanup 调用复用正常调用的参数串)。

### 改动 2:框架 `task.py` 透传已替换的 run_script 前缀

在 `SingleTask.__init__`(`:648` 的 `self.running_config` 字典)增加一项:
```python
"run_script_prefix": self._resolved_run_script_prefix(config),
```
其中新增方法 `_resolved_run_script_prefix(self, config)`:
- 取 `config.run_script`(TaskConfig 属性,`task.py:104`);若为 None 返回 None。
- 复用 `filter_command_line` 同款截断:若 `run_script` 含 `| ignore_cmd_redirect`,截掉该尾巴(参考 `utils.py:345-346`)。
- 用 `self._form_line(run_script, config)`(`task.py:803`)做变量替换,得到形如 `python /path/run_cross_compilation.py --tool=adb --device=xxx` 的可执行前缀串。
- 注意:需拿到含 `internal_var` 的 config。`SingleTask.__init__` 里 `config = config.get_case_config(case)`(`:618`)已含 `internal_var` 与 `f`/`n`。用此 config 调 `_form_line`。

  → 但 `_form_line` 是 `@staticmethod`,签名 `(line, config)`,内部 `config.get("internal_var")`。`get_case_config` 返回的 dict 有 `internal_var` 键(`task.py:136`),可用。

兼容:未配 `[run] script` 的套,`config.run_script` 为 None,`run_script_prefix` 为 None,钩子跳过。

### 改动 3:框架 `run.py` 在 case 成功结束后调用钩子

`run_commands`(`run.py:170`)签名增加可选参数:
```python
def run_commands(position, old_result, commands, case_path, work_dir, timeout, log_config, env=None, run_script_prefix=None):
```
通过 `**task.running_config` 自动接收(`serial_run_task`/`parallel_run_task` 调用处无需改动)。

在 `:247` 的 PASS 分支,删本地 work_dir 之前插入:
```python
if result[0] == PASS:
    if run_script_prefix and not configs.get_val('keep_temp'):
        cleanup_cmd = '{} --cleanup'.format(run_script_prefix)
        try:
            # 复用本文件已有的 run_command_win/run_command_linux
            run_command = run_command_win if platform.system() == "Windows" else run_command_linux
            run_command(cleanup_cmd, work_dir, 60, logger, env, None)
        except Exception as e:
            logger.debug("Remote cleanup skipped for {}: {}".format(work_dir, e))
    if not configs.get_val('keep_temp'):
        # 原有 shutil.rmtree(work_dir) 逻辑不动
```

- 清理超时给 60 秒(hdc rm 很快,留足余量)。
- 任何异常只记 debug 日志,不阻断 case 结果(case 已 PASS)。
- `keep_temp` 为真时设备目录也保留,与本地 work_dir 行为一致。

### 数据流图
```
cfg [run] script (模板,含 %%python/%%DEVICE_ID)
   ↓ TaskConfig.run_script (task.py:104, configparser 已 %%→%)
   ↓ SingleTask.__init__ → _resolved_run_script_prefix:
       截断 | ignore_cmd_redirect + _form_line 变量替换
   ↓ running_config["run_script_prefix"] = "python /.../run_cross_compilation.py --tool=adb --device=xxx"
   ↓ run_commands(**running_config) 自动展开 run_script_prefix 形参
   ↓ case PASS 分支 → 调 run_script_prefix + " --cleanup"
   ↓ 脚本 --cleanup:os.getcwd() basename = 设备目录名 → rm -rf
```

## 兼容性与影响面
- **普通本地测试套**(无 `[run] script`):`run_script_prefix` 为 None,钩子跳过,零影响。
- **配了 script 的旧脚本**(无 `--cleanup`):框架调 `--cleanup` 时旧脚本的 argparse 会因未知参数 `--cleanup` 报错 → 被 try/except 捕获,仅记 debug 日志,case 结果不变(已 PASS)。**不破坏现有运行**,只是旧脚本套不享受设备清理。升级脚本即生效。
- `keep_temp` 同时控制本地与设备清理,语义一致。
- 失败 case:仍由脚本自身清理(`run_cross_compilation.py:265-270`),行为不变;框架钩子只在 PASS 触发,不会重复清理(失败时 result[0] != PASS)。

## 验证清单
1. android case PASS 后:`hdc shell ls /data/local/tmp/run/<work_dir>` 应 No such file。
2. `--keep_temp`:设备目录保留。
3. case FAIL:脚本自身清理(行为不变)。
4. 普通本地 case:不受影响(钩子跳过)。
5. `run_script_prefix` 变量替换正确(设备参数真实传入,不残留 `%DEVICE_ID`)。

## 改动文件清单
- `testsuites/HLT/configs/cjnative/run_cross_compilation.py`:加 `--cleanup` 模式。
- `maple_test/task.py`:`SingleTask.__init__` running_config 加 `run_script_prefix`;新增 `_resolved_run_script_prefix`。
- `maple_test/run.py`:`run_commands` 加 `run_script_prefix` 形参 + PASS 分支钩子。
