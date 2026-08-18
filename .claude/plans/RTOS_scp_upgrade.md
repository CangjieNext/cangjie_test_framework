# RTOS 板卡支持：run_cross_compilation.py 升级 scp 传输 + --cleanup 清理

> **状态：已实现（2026-08-31）**。改动落地于 `run_cross_compilation.py` + 新增 RTOS cfg，框架侧零改动。实现说明见 `talkless/docs/测试执行-RTOS板卡scp传输与远端清理.md`。
>
> **更新（2026-09-02）：执行环境迁移到 Linux host**（框架跑在 docker 内，板卡经 `ssh -p 2222 root@127.0.0.1` 访问）。cfg 目录 `windows_x64-rtos_aarch64` 已 `git mv` 为 `linux_x64-rtos_aarch64`：host 侧变量全部 Linux 化（`host=linux_x86_64_cjnative`、`host_triple=x86_64-unknown-linux-gnu`、`ls/cat/rm/cp` 等换 POSIX 命令、compiler/cjfmt 等加 host+runtime LD_LIBRARY_PATH 包装），`[run] script` 改用 POSIX 环境变量语法 `%%python $CANGJIE_TEST/... --tool=scp --host=${RTOS_HOST} --user=${RTOS_USER} --port=${RTOS_PORT} --remote-root=/tmp/run`。`run_cross_compilation.py` 追加两处修复：1) `convert_windows_path_separators` 仅在 Windows host 生效（POSIX host 上反斜杠是 shell 转义符，转换会破坏用例命令）；2) ssh/scp 统一加 `-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null`（板卡 host key 变化/首次连接时避免交互提示导致连接失败）。
>
> **更新（2026-09-02 晚）：实际目标是 armv7a（32 位 ARM，非 aarch64）**。用户确认的实际编译命令：`cjc main.cj --target=armv7a-huawei-hongmeng-musleabi --toolchain=/opt/buildtools/bisheng_embedded_cpu-305.0.0/BiSheng_arm32le_hm/bin --sysroot=/opt/RTOS_NEXT/301.1.0/arm32A9le_hm_micro/sdk -o main`。工作落在新分支 `0902_rtos`（基于 main），cfg 目录为 `linux_x64-rtos_aarch32`：condition 用 `arm`+`target_aarch32`，runtime 目录名按命名惯例推断为 `linux_rtos_arm_cjnative`（docker 内 `ls $CANGJIE_HOME/runtime/lib/` 与板卡 `/data/local/tmp/` 需人工确认），工具链/sysroot 路径按用户命令硬编码进 `ohos_opt`/`clang`/`clang_opt`/`check-dylib-dep`/`prebuilt-toolchain`。旧分支 0831_fix_case 上的 `linux_x64-rtos_aarch64`（aarch64 版）已过时，勿合并。
>
> **重要流程纠正（2026-09-02 深夜）：HLT 下的 cfg 不是手改的，而是由生成器产出**。cfg 源在 `E:\talkless\test_config`（cjpm 项目）：平台源模块 `src/<platform>/basic.cj`（`test_config.common` 提供 HostLinux/HostWindows/HostMac 基类，`test_config.config` 提供 Config/condition/BuildProfile 机制），`cjpm run` 运行 `src/main.cj` 的 `generate()`，把全量 cfg 写进 `cjnative_main`/`cjnative_jd`/`cjnative_icsl`/`cjnative_release1.0`/`cjnative_release1.1` 五个分支目录（HLT 仓库同步自 `cjnative_main`）。本次：删除 `src/windows_x64_rtos/`，新增 `src/linux_x64_rtos/basic.cj`（HostLinuxConfig 基类 + armv7a），并在 `common_config.cj`（target/target_ls/suffix/target_cp/target_cat/target_shell/dylib_suffix/syntax_extra_options 八处）与 `config.cj`（targetConditions/link_openssl 两处）补 armv7a 分支；`main.cj` 的 dump 目标改为 `linux_x64-rtos_aarch32/{basic,O2,static_O2}.cfg`；旧的 `windows_x64-rtos*` 产物与仓库内旧目录一并删除。
>
> **更新（2026-09-02 深夜）：scp 上传不带用例临时目录名（已回退）**。曾把远端用例目录改成 remote root 本身（`scp -r <work_dir>/. user@host:/tmp/run`），但批量跑时用例互相 `rm -rf /tmp/run` 造成冲突，**已回退为每用例独立目录**：远端布局为 `remote_root/<work_dir basename>`（如 `/tmp/run/case_<哈希值>`）。
>
> **更新（2026-09-02 深夜·最终形态）：scp 目标只能写 remote root**。板卡上的 scp 不接受 `/tmp/run/<hash-dir>` 作为目标，只接受已存在的 `/tmp/run`：copy 阶段先 `ssh mkdir -p /tmp/run` 确保 root 存在，再 `scp -r <work_dir> user@host:/tmp/run`——scp 自动把本地目录作为子目录拷入，远端得到 `/tmp/run/<hash-dir>`。run_case 用 `cd /tmp/run/<hash-dir>`，`--cleanup`/失败清理只 `rm -rf /tmp/run/<hash-dir>`，绝不删 remote root；hdc/adb 行为不变（仍传完整 `remote_case_dir`）。这样并行批量跑互不覆盖。

## 背景与目标

测试框架需要支持 RTOS 板卡作为目标设备。RTOS 板卡上有 sshd，可通过 `scp` 实现文件传输（如 `scp D:\app.bin root@192.168.1.50:/tmp/`、`scp root@192.168.1.50:/tmp/board.log D:\logs\`）。现有 `run_cross_compilation.py` 仅支持 hdc/adb 两种工具，需升级为支持 scp。

同时，用户强调：**用例执行完毕后必须将远端临时目录删除干净，否则占用存储空间**。经核查，框架侧（`cangjie_test_framework/maple_test/run.py:248-272`）**已经实现了 `--cleanup` 清理机制**——用例 PASS 且未开 `keep_temp` 时，框架会以 `run_script_prefix --cleanup` 重新调用 run 脚本清理远端目录，再 `shutil.rmtree` 清理本地 work_dir。**但 `run_cross_compilation.py` 的 `parse_cli()` 没有声明 `--cleanup` 参数**，导致 argparse 对 `--cleanup` 报 "unrecognized arguments" 错误，框架在 `run.py:264` 的 except 里把这个错误静默吞掉（只打 debug 日志 "Remote cleanup skipped"）。结果是：**现有 hdc/adb 目标的远端清理其实一直是失败的**，RTOS 上若不修复，远端目录会持续堆积。

因此本任务有两重目标：
1. **升级 `run_cross_compilation.py` 支持 scp 传输**（新增 tool=scp 分支）。
2. **修复 `--cleanup` 接收端**，使框架既有的清理机制对 scp（及 hdc/adb）真正生效，确保远端目录在用例结束后被 `rm -rf` 删干净。

## 关键事实（已核查）

- **框架清理机制已就绪**：`run.py:248-272`，PASS+非keep_temp 时调 `run_script_prefix --cleanup`（timeout = min(timeout,60)）清理远端，再 rmtree 本地。`run_script_prefix` 由 `_resolved_run_script_prefix`（task.py:676-698）生成——去掉 `| ignore_cmd_redirect` 后缀、展开 `%key` 内部变量、保留 `$ENV`/`${ENV}` 给宿主 shell。
- **远端路径推导依据**：`run_cross_compilation.py:334-335` `remote_path = os.path.basename(os.getcwd())`。框架在原 work_dir 执行清理命令（run.py:262 `run_command(cleanup_cmd, work_dir, ...)`），所以 `--cleanup` 时 `os.getcwd()` 的 basename 与用例执行时一致 → 能定位到同一远端目录。**前提：清理必须在 rmtree 本地 work_dir 之前发生**（run.py 已保证此顺序）。
- **scp 连接信息**：用环境变量 `RTOS_HOST`/`RTOS_USER`（沿用现有 `DEVICE_ID` 模式），cfg 里写 `--device=%%RTOS_HOST%%` 或新增 `--host`。已确认决策：环境变量方案。
- **传输对象**：`scp -r` 传整个 work_dir 目录（与 hdc `file send` 一致）。已确认决策。
- **清理范围**：`rm -rf` 删整个用例远端目录 `/data/local/tmp/run/<basename>`。已确认决策。
- **OHOS 默认 tool=hdc**：cfg 的 `[run] script` 不写 `--tool` 时，脚本第38行 `tool = "hdc"` 默认。Android 写 `--tool=adb`。

## 实现方案

### 改动 1：`run_cross_compilation.py` 新增 scp 工具支持

文件：`E:\cangjie_test_suite\cangjie_test\testsuites\HLT\configs\cjnative\run_cross_compilation.py`

#### 1.1 `parse_cli()` 新增连接参数与 `--cleanup`

在 `connection_options` 组里新增 scp 相关参数，并新增 `--cleanup` 开关：

```python
connection_options.add_argument("--host", type=str, default=None,
    help="scp target host (e.g. 192.168.1.50), can also be set via RTOS_HOST env")
connection_options.add_argument("--user", type=str, default=None,
    help="scp target user (e.g. root), can also be set via RTOS_USER env")
connection_options.add_argument("--port", type=str, default=None,
    help="scp/ssh port, can also be set via RTOS_PORT env")
connection_options.add_argument("--remote-root", type=str, default="/data/local/tmp/run",
    help="remote root dir for case run (default /data/local/tmp/run)")
connection_options.add_argument("--cleanup", action="store_true", default=False,
    help="cleanup mode: remove the remote case dir and exit (invoked by framework after case pass)")
```

注意：`execute_cmd` 是 `nargs=argparse.ONE_OR_MORE` 的位置参数。**`--cleanup` 模式下不传 execute_cmd**，需要把它改为可选：`nargs=argparse.ZERO_OR_MORE`（或 `'*'`），否则 `--cleanup` 单独调用时 argparse 会因缺位置参数报错。

#### 1.2 新增 scp 命令构造函数

仿照 `construct_tool_send_cmd`（hdc/adb 分支）新增 scp 分支：

```python
def construct_scp_send_cmd(src, dest, host, user, port):
    target = "{}@{}:{}".format(user, host, dest)
    port_opt = "-P {} ".format(port) if port else ""
    # src 是本地 work_dir，dest 是远端目录；scp -r 递归传整个目录
    return "scp -r {}{} {}".format(port_opt, src, target)

def construct_scp_recv_cmd(src, dest, host, user, port):
    target = "{}@{}:{}".format(user, host, src)
    port_opt = "-P {} ".format(port) if port else ""
    return "scp -r {}{} {}".format(port_opt, target, dest)
```

scp 的远端 shell 命令（run_case / remove）通过 `ssh` 执行，而非 hdc shell。新增：

```python
def construct_ssh_shell_cmd(cmd, host, user, port):
    # 与 construct_tool_shell_cmd 的 stdout/stderr/exit_code 捕获机制一致，
    # 但通过 ssh 在远端执行
    remote_temp_dir = '/tmp'  # RTOS 上 /tmp 可写
    h = '{}/{}'.format(remote_temp_dir, uuid.uuid4())
    shell_cmd = f'{cmd} 1> {h}_stdout.txt 2> {h}_stderr.txt ; echo exit_code_start$?exit_code_end > {h}_exit_code.txt ; cat {h}_stdout.txt ; cat {h}_exit_code.txt ; cat {h}_stderr.txt ; rm {h}_stdout.txt ; rm {h}_exit_code.txt ; rm {h}_stderr.txt'
    port_opt = "-p {} ".format(port) if port else ""
    return 'ssh {}{}@{} {}'.format(port_opt, user, host, shlex.quote(shell_cmd))
```

#### 1.3 改造 `construct_remote_cmd` 增加 scp 分支

现有函数硬编码 `/data/local/tmp/run/` 与 hdc shell。改造为：根据 tool 选择 send/shell 构造器，远端根目录用 `remote_root` 参数（默认 `/data/local/tmp/run`，RTOS 可配 `/tmp` 等）。

#### 1.4 改造 `main()`：处理 `--cleanup` 与 scp 连接解析

```python
def main():
    opts = parse_cli()
    # 解析 scp 连接信息：CLI > 环境变量
    host = opts.host or os.environ.get("RTOS_HOST")
    user = opts.user or os.environ.get("RTOS_USER")
    port = opts.port or os.environ.get("RTOS_PORT")
    tool = opts.tool
    if tool == "scp":
        if not host or not user:
            raise RunError("scp tool requires --host/RTOS_HOST and --user/RTOS_USER")
    # ... hdc/adb device 拼接逻辑保留 ...

    local_path = os.getcwd()
    remote_path = os.path.basename(local_path)

    # ---- cleanup 模式：只删远端目录然后退出 ----
    if opts.cleanup:
        remove_cmd = "rm -rf {}/{}".format(opts.remote_root.rstrip('/'), remote_path)
        if tool == "scp":
            cleanup_cmd = construct_ssh_shell_cmd(remove_cmd, host, user, port)
        else:
            cleanup_cmd = construct_tool_shell_cmd(remove_cmd)
        run_cmd("remove_file_on_remote", cleanup_cmd, ".", opts.timeout or 60)
        return  # 清理完直接退出，不执行用例

    # ---- 正常执行模式（现有逻辑）----
    execute_cmd = " ".join(opts.execute_cmd)
    ...
```

#### 1.5 `convert_windows_path_separators` 对 scp 命令的影响核查

`convert_windows_path_separators` 会把 `\` 转 `/`，但 scp 命令里的 `root@host:/path` 含 `:` 和 `@`，不在 `path_chars` 里，`\` 处理不影响这些字符。**但 scp 的远端路径 `/tmp/...` 不会被破坏**（无反斜杠）。需确认本地 src 路径在 Windows 下用反斜杠时 scp 能接受——scp 在 Windows 上由 OpenSSH 客户端处理，反斜杠路径需转正斜杠。**结论：scp 命令不经过 `convert_windows_path_separators`**（该函数只应作用于 execute_cmd，即用例的运行命令，不作用于 send/recv/shell 构造命令）。现有代码也只在 `execute_cmd` 上调用它（第315行），send_cmd 不经过它，**保持这一边界即可**。

### 改动 2：新增 RTOS cfg 配置文件

在 `E:\cangjie_test_suite\cangjie_test\testsuites\HLT\configs\cjnative\` 下新增 RTOS 配置目录（如 `windows_x64-rtos_aarch64/`），`[run]` 段：

```
[run]
	script = python %%CANGJIE_TEST%%/testsuites/HLT/configs/cjnative/run_cross_compilation.py --tool=scp --host=%%RTOS_HOST%% --user=%%RTOS_USER%% | ignore_cmd_redirect
	pass_redirect = true
```

`[internal-var]` 里 `%run` 等仍按现有定义（RTOS 上运行可执行文件的环境变量设置）。`[condition]` 段加 `target_rtos` 等条件标签。

### 改动 3（可选）：框架侧无需改动

`run.py` 的 `--cleanup` 调用逻辑已正确，`task.py` 的 `run_script_prefix` 生成已正确。**框架侧无需改动**。唯一要确认：`run_script_prefix` 展开后是 `python .../run_cross_compilation.py --tool=scp --host=<RTOS_HOST值> --user=<RTOS_USER值>`，框架拼 ` --cleanup` 后变成完整命令，argparse 能正确解析。`%%RTOS_HOST%%` 在 cfg 里经 configparser 降为 `%RTOS_HOST`，再经 `_form_line` 不展开（因为 RTOS_HOST 不在 internal_var 里，是 shell 环境变量），留给宿主 shell 展开——与现有 `${DEVICE_ID}` 模式一致。

## 验证步骤

1. **argparse 解析**：手动跑 `python run_cross_compilation.py --tool=scp --host=... --user=... --cleanup`，确认不报 unrecognized arguments、且进入 cleanup 分支。
2. **scp 传输**：准备一个含可执行文件的小 work_dir，跑正常执行模式，确认 `scp -r` 把目录传到板卡 `/tmp/run/<basename>`。
3. **远端执行**：确认 ssh 执行用例命令、exit_code 捕获正确（与 hdc 一致）。
4. **清理**：用例 PASS 后确认框架调 `--cleanup`、板卡上对应目录被 `rm -rf` 删除、本地 work_dir 也被 rmtree。
5. **回归 hdc/adb**：跑一个现有 OHOS/Android 用例，确认未破坏现有 tool 分支（含 `--cleanup` 现在也能正确执行而非被静默吞掉）。

## 影响面

- **核心改动集中在 `run_cross_compilation.py` 一个文件**（parse_cli、construct_*、main）。
- 新增 RTOS cfg 目录，不触碰现有 cfg。
- 框架侧（cangjie_test_framework）零改动。
- 副作用：修复了 hdc/adb 目标原本失效的远端清理（现在 `--cleanup` 能正确执行），这是正向改进。
