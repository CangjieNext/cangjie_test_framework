# 代码安全检视报告

> 仓库：`cangjie_test_framework`
> 检视范围：`main.py`、`maple_test/{main,task,run,configs,utils,test,compare,__init__}.py`
> 检视日期：2026-07-28
> 检视内容：安全写法 / 健壮性问题

---

## 一、问题清单（按严重程度）

| 序号 | 严重程度 | 问题 | 位置 |
| :--: | :------: | :--- | :--- |
| 1 | 🔴 高危 | 路径穿越导致任意文件写入 | `maple_test/task.py:686-697` |
| 2 | 🟠 中危 | `eval()` 执行字符串表达式 | `maple_test/utils.py:301` |
| 3 | 🟠 中危 | Windows 命令引号转义不完整（命令注入风险） | `maple_test/utils.py:477-481` |
| 4 | 🟡 低危 | `shell=True` + 字符串拼接执行命令 | `maple_test/run.py:85-94, 129-141` |
| 5 | 🟡 低危 | 裸 `except: pass` 吞掉所有异常 | `maple_test/task.py:753-755` |
| 6 | 🟡 低危 | `os.system` 执行命令 | `maple_test/run.py:104` |
| 7 | 🟡 低危 | `sys.output` 赋值无效（笔误） | `maple_test/main.py:28` |
| 8 | 🟡 低危 | `os.path.expandvars` 展开环境变量值 | `maple_test/task.py:128-129` |
| 9 | 🟡 低危 | 可预测的临时目录名 | `maple_test/task.py:623` |
| 10 | 🟡 低危 | ReDoS / `unicode_escape` 风险 | `maple_test/compare.py:360, 382-383, 432-433` |

---

## 二、问题详情与修复建议

### 🔴 1. 路径穿越导致任意文件写入

**位置**：`maple_test/task.py:686-697`（`separate_by_files`）

**问题代码**：

```python
@staticmethod
def separate_by_files(separation, dest, logger, config):
    if separation == []:
        return

    for filepath, content in separation:
        filepath = SingleTask._form_line(filepath, config)
        path = os.path.normpath(dest / filepath)   # ← 无边界校验
        (dir, file) = os.path.split(path)
        SingleTask.prepare_dir(Path(dir))
        with open(path, "w") as file:
            file.write(content)
```

**风险**：
`filepath` 来源于测试用例文件里的 `// SEPARATE-FILE: <path>` 指令（见 `test.py:98-136` 的 `extract_separation_by_files`），`content` 是其后跟随的用例正文。`os.path.normpath(dest / filepath)` 在 `filepath` 含 `../../` 时会解析到 `dest` 之外，例如：

```
// SEPARATE-FILE: ../../../../etc/cron.d/poc
<任意内容>
```

会把任意内容写到 `/etc/cron.d/poc`，`prepare_dir` 还会顺带创建沿途目录，构成任意文件写入漏洞。

**修复建议**：
解析后强制校验结果路径必须仍在 `dest` 内：

```python
@staticmethod
def separate_by_files(separation, dest, logger, config):
    if separation == []:
        return

    dest_resolved = dest.resolve()
    for filepath, content in separation:
        filepath = SingleTask._form_line(filepath, config)
        path = (dest / filepath).resolve()
        try:
            path.relative_to(dest_resolved)
        except ValueError:
            raise TestError(
                "SEPARATE-FILE path escapes work dir: {}".format(filepath)
            )
        SingleTask.prepare_dir(path.parent)
        with open(path, "w") as f:
            f.write(content)
```

---

### 🟠 2. `eval()` 执行字符串表达式

**位置**：`maple_test/utils.py:301`（`process_condition`）

**问题代码**：

```python
try:
    return eval(cur_con)
except SyntaxError as e:
    raise ValueError(f"Invalid syntax in '{original_expr}': {e}")
```

**风险**：
虽然前面用 `re.findall` + 白名单（`and/or/not/True/False`）做了清洗，原则上只剩布尔运算符，但 `eval` 本身是不安全写法，且正则替换存在边角情况。

**修复建议**：
改用安全求值器，例如基于 `ast.parse` 仅允许有限节点类型：

```python
import ast

_BOOL_OPS = {ast.And: all, ast.Or: any}

def _safe_eval(node, conditions):
    if isinstance(node, ast.BoolOp):
        return _BOOL_OPS[type(node.op)](
            [_safe_eval(v, conditions) for v in node.values]
        )
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _safe_eval(node.operand, conditions)
    if isinstance(node, ast.Name):
        return node.id in conditions
    raise ValueError("disallowed node in expression")

# 替换 eval(cur_con):
return _safe_eval(ast.parse(cur_con, mode='eval').body, conditions)
```

---

### 🟠 3. Windows 命令引号转义不完整（命令注入风险）

**位置**：`maple_test/utils.py:477-481`（`quote`）

**问题代码**：

```python
def quote(original_string):
    if platform.system() == "Windows":
        return '"' + escape('\\"', original_string) + '"'   # ← 只转义 "
    else:
        return shlex.quote(original_string)
```

**风险**：
Linux 走 `shlex.quote`（安全）；Windows 只转义双引号，对 `& | < > % ^` 等 cmd 元字符不做处理。该函数用于 `task.py:774-783` 构造 `--comment={quote(case.comment)}`，整条命令随后以 `shell=True` 执行（`run.py:85-94`）。若 `comment`（来自 cfg 的 `suffix` 段）含 `& whoami` 之类，在 Windows 上会触发命令注入，与 Linux 行为不一致。

**修复建议**：
Windows 下用 `subprocess.list2cmdline` 或对 cmd 元字符集统一转义；更彻底的做法是避免 `shell=True`，改为列表传参。

```python
def quote(original_string):
    if platform.system() == "Windows":
        # 转义 cmd 元字符并转义双引号
        unsafe = '\\"&|<>%^'
        escaped = original_string.replace('"', '\\"')
        for ch in unsafe:
            escaped = escaped.replace(ch, '^' + ch)
        return '"' + escaped + '"'
    else:
        return shlex.quote(original_string)
```

---

### 🟡 4. `shell=True` + 字符串拼接执行命令

**位置**：`maple_test/run.py:85-94`、`maple_test/run.py:129-141`

**问题**：
命令由用例 `EXEC`/`RUN` 指令经 `_form_line` 变量替换后以 `shell=True` 执行。测试框架"运行用例中声明的命令"属预期行为，但变量值（来自 cfg 的 `internal-var`、`-C key=value`）若含 shell 元字符会被解释。

**建议**：
在可信配置前提下风险可接受，但建议对框架自身可控的拼接（如 `compare_cmd`）尽量用列表参数 + `shell=False`。

---

### 🟡 5. 裸 `except: pass` 吞掉所有异常

**位置**：`maple_test/task.py:753-755`（`prepare_dependence` 内 `shutil.copytree`）

**问题代码**：

```python
try:
    shutil.copytree(str(file), str(dest / name))
except:
    pass
```

**风险**：
任何错误（含权限/路径异常）都被静默忽略，掩盖真实问题，调试困难。

**修复建议**：
定向捕获并记录：

```python
try:
    shutil.copytree(str(file), str(dest / name))
except shutil.Error as e:
    logger.debug("copytree failed for {}: {}".format(file, e))
```

---

### 🟡 6. `os.system` 执行命令

**位置**：`maple_test/run.py:104`

**问题代码**：

```python
os.system('taskkill /t /f /pid {}'.format(process_command.pid))
```

**风险**：
`pid` 是整数当前不可注入，但 `os.system` 走 shell，脆弱且无法捕获返回值，属于不良写法。

**修复建议**：

```python
subprocess.run(
    ['taskkill', '/t', '/f', '/pid', str(process_command.pid)],
    capture_output=True,
)
```

---

### 🟡 7. `sys.output` 赋值无效（笔误）

**位置**：`maple_test/main.py:28`

**问题代码**：

```python
sys.output = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')
```

**风险**：
应为 `sys.stdout = ...`。当前写法新建了一个无引用的 `sys.output` 属性，UTF-8 包装并未生效，Windows 下可能与编码处理逻辑预期不符。

**修复建议**：

```python
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')
```

---

### 🟡 8. `os.path.expandvars` 展开环境变量值

**位置**：`maple_test/task.py:128-129`

**问题代码**：

```python
os.environ[i] = os.path.expandvars(envs[i])
self.env.update({i: os.path.expandvars(envs[i])})
```

**风险**：
cfg/env 值中若含 `$VAR`/`${VAR}` 会被展开。预期可能是字面量时会产生意外替换，并把这些值带入后续 shell 命令。

**建议**：
确认是否需要展开；不需要则直接赋原值。若需展开，应保证展开后的值不会引入 shell 元字符。

---

### 🟡 9. 可预测的临时目录名

**位置**：`maple_test/task.py:623`

**问题代码**：

```python
self.temp_dir = "{}_{}".format(self.path.name.replace(".", "_"), int(time.time()))
```

**风险**：
`normal` 模式用 `time.time()` 命名，可预测，存在符号链接竞态可能。`tile` 模式用 `uuid` 较好。

**修复建议**：
统一用 `uuid` 或 `tempfile.mkdtemp`：

```python
import tempfile
self.temp_dir = "{}_{}".format(self.path.name.replace(".", "_"), uuid.uuid1().hex)
```

---

### 🟡 10. ReDoS / `unicode_escape` 风险

**位置**：`maple_test/compare.py:360`、`382-383`、`432-433`

**问题代码**：

```python
# scan_match / full_match 中对用例控制的 pattern 做了 unicode_escape 解码
pattern = re.sub(r'([^Ā-￿]+)',
                 lambda x: (x.group(1) + r' ').encode("utf-8").decode("unicode_escape")[:-1], pattern)

# regex_match 中 pattern 来自用例
matches = re.finditer(str(pattern), content, re.MULTILINE)
```

**风险**：
`decode("unicode_escape")` 可能把 `\uXXXX` 序列解释为控制字符；`re.compile(pattern)` 的 pattern 来自用例，存在病态正则导致 ReDoS（正则拒绝服务）的可能。测试工具场景下风险较低，但仍属不良写法。

**建议**：
- 限制 pattern 长度/复杂度，或对 `re.compile` 加超时保护。
- 评估是否真的需要 `unicode_escape` 解码，若不需要则移除。

---

## 三、做得不错的地方

- ✅ XML 用 `ElementTree` API 构造（非字符串拼接），无 XXE / 注入风险。
- ✅ JSON 用 `json.dump`，无注入风险。
- ✅ 未使用 `pickle`、`yaml.load` 等高危反序列化。
- ✅ Linux 下用 `shlex.quote` 转义，并 `start_new_session=True` + `os.killpg` 做了进程组清理。
- ✅ 配置继承有环路检测（`task.py:78-80` 的 `CONFIG_SET`）。

---

## 四、修复优先级

| 优先级 | 序号 | 问题 | 处置 |
| :----: | :--: | :--- | :--- |
| **P0 必修** | 1 | 路径穿越导致任意文件写入 | 加 `relative_to` 边界校验 |
| **P1 建议修** | 2 | `eval()` 替换为 AST 求值 | 去除 `eval` |
| **P1 建议修** | 3 | Windows `quote` 转义补全 | 补全 cmd 元字符转义 |
| **P1 建议修** | 5 | 裸 `except` 改为定向捕获 | 至少记录日志 |
| **P2 可选** | 6 | `os.system` → `subprocess.run` | 改用列表传参 |
| **P2 可选** | 7 | 修正 `sys.output` 笔误 | 改为 `sys.stdout` |
| **P2 可选** | 4 | `shell=True` 收敛 | 框架可控拼接改用列表参数 |
| **P2 可选** | 8 | `expandvars` 确认必要性 | 按需保留 |
| **P2 可选** | 9 | 临时目录命名统一用 `uuid` | 改用 `uuid` / `mkdtemp` |
| **P2 可选** | 10 | ReDoS / `unicode_escape` 收敛 | 限制复杂度 + 超时 |
