# Maple 测试框架

本项目测试框架为方舟编译器开源测试框架：https://gitee.com/openarkcompiler/OpenArkCompiler/tree/master/test

## 目录结构

```shell
cangjie_test_framework/
|-- README.md           # 测试框架说明
|-- main.py             # 运行测试套入口
`-- maple_test          # 测试框架代码
   |--__init__.py
   |--compare.py        # 结果校验模块   
   |--configs.py        # 参数设置与框架配置文件模块
   |--main.py           # 内部入口
   |--maple_test.cfg    # 测试框架配置文件
   |--run.py            # 命令运行模块
   |--task.py           # 测试任务准备与运行模块
   |--template.cfg      # 测试套配置文件模板
   |--test.py           # 测试用例模块
   `--utils.py          # 通用模块
```

## 运行要求

* `python` 版本>=3.5.2
* `llvm-15.0.4`
* 

## 修改框架配置

文件：`maple_test.cfg`

```ini
# 测试框架配置文件，当前框架仅支持通过配置文件配置测试套，测试运行时的临时路径，测试日志的保存
[test-home]
# 指定测试套路径，以‘：’划分
dir = 
    ../../cangjie_test/testsuites/HLT:../../cangjie_test/testsuites/LLT

[running]
# 指定运行时的临时路径
temp_dir = ../test_temp/run

[logging]
# 指定运行时保存日志的路径
name = ../test_temp/log
level = INFO
```

## 运行说明

测试用例运行依赖：

* 仓颉工具链：[安装仓颉工具链](https://gitcode.com/Cangjie/cangjie_docs/blob/main/docs/dev-guide/source_zh_cn/first_understanding/install.md)
* `Git Bash` 需配置到 `Path` 环境变量
* `python` 库：`pexpect` 模块和 `fasteners` 模块
* `OpenSSL 3` 的 `ssl` 和 `crypto` 的动态库文件
* `JDK`
* `llvm`
* `MinGW-w64`

下载测试用例：

```shell
git clone https://gitcode.com/Cangjie/cangjie_test.git
```

下载测试框架：

```shell
git clone https://gitcode.com/Cangjie/cangjie_test_framework.git
```

以下运行示例都在 `Linux x86_64` 环境下运行，如需更换运行环境需选取对应测试环境的配置文件

### 运行单个 `testsuites/HLT` 用例

```shell
python3 cangjie_test_framework/main.py --test_cfg=cangjie_test/testsuites/HLT/configs/cjnative/cangjie2cjnative_linux_x86_test.cfg --verbose cangjie_test/testsuites/HLT/compiler/cjnative/Chir/ForIn/for_in_01.cj
```

### 运行单个 `testsuites/HLT/Tools/cjlsp` 用例

执行 `LSP` 用例需要将 `CANGJIE SDK` 包中的 `modules` 目录拷贝至 `tools/bin` 路径下

```shell
cp -r ${CANGJIE_HOME}/modules ${CANGJIE_HOME}/tools/bin
```

修改 `cangjie_test/testsuites/HLT/Tools/cjlsp/lsp_config.txt` 配置文件中的 `lsp_server` 路径，将占位符替换为 `${CANGJIE_HOME}/tools/bin` 的绝对路径

```ini
[lsp_server]
    win_path = ${win_lsp_server_path} 	   // Windows环境执行修改此处
    linux_path = ${linux_lsp_server_path}  // Linux或MAC环境执行修改此处
```

剩余执行步骤与其他用例无区别

### 运行 `testsuites/HLT` 文件夹内的所有用例

```shell
python3 cangjie_test_framework/main.py --test_cfg=cangjie_test/testsuites/HLT/configs/cjnative/cangjie2cjnative_linux_x86_test.cfg --test_list=cangjie_test/testsuites/HLT/testlist -pFAIL -j20 --timeout=180 cangjie_test/testsuites/HLT/ 
```

### 运行已配置的所有测试套

准备测试套默认配置文件

```shell
cp cangjie_test/testsuites/HLT/configs/cjnative/cangjie2cjnative_linux_x86_test.cfg cangjie_test/testsuites/HLT/test.cfg
cp cangjie_test/testsuites/LLT/configs/cjnative/cjnative_test.cfg cangjie_test/testsuites/LLT/test.cfg
```

修改配置文件 `root` 路径：

* `cangjie_test/testsuites/HLT/test.cfg`
* `cangjie_test/testsuites/LLT/test.cfg`

```ini
[root]
  path = ./
```

同时运行 `testsuites/HLT` 和 `testsuites/LLT` 测试套

```shell
python3 cangjie_test_framework/main.py -pFAIL -j20 --timeout=180
```

参数说明：指定参数会覆盖框架配置文件中的设置

```shell
usage: main.py [-h] [--cfg CFG] [-j <num>] [--retry <num>] [--output <file>] [--xml_output <file>] [--json_output <file>] [--debug] [--keep_temp] [--compatible] [--fail_exit] [--pass_rate <num>] [--transfer] [--condition [CONDITION]] [--level [LEVEL]]
               [-p {PASS,FAIL,XFAIL,XPASS,UNSUPPORTED,UNRESOLVED}] [--progress {silent,normal,no_flush_progress}] [--test_cfg <TEST_CFG_FILE>] [--test_list <TEST_LIST_FILE>] [-C key=value] [-E key=value] [--temp_dir <TEMP_DIR_PATH>]
               [--directory_list <DIRECTORY_LIST_PATH>] [--timeout TIMEOUT] [--directory_structure {tile,normal}] [--log_dir <LOG_DIR_FILE_PATH>] [--log_level LOG_LEVEL] [--verbose] [--fail-verbose] [--split SPLIT] [--run_split RUN_SPLIT]
               [--check <CHECK_TEST_CASE>]
               [test_paths ...]

options:
  -h, --help            show this help message and exit

Test FrameWork arguments:
  --cfg CFG             Test framework configuration file
  -j <num>              Run <num> cases in parallel
  --retry <num>         Re-run unsuccessful test cases
  --output <file>       Store test result at <file>
  --xml_output <file>   Store test result as xunit xml format at <file>
  --json_output <file>  Store test result as json format at <file>
  --debug               only keep failed temp file
  --keep_temp           keep all test temp file
  --compatible          test different versions of cjc
  --fail_exit           Execute test framework with a non-zero exit code if any tests fail
  --pass_rate <num>     Set the pass rate of test cases
  --transfer            Help transfer negative case to new version.
  --condition [CONDITION]
                        Input condition for run, default empty.
  --level [LEVEL]       Input level for run, default empty.
  -p {PASS,FAIL,XFAIL,XPASS,UNSUPPORTED,UNRESOLVED}
                        Print test cases with specified results, -pPASS -pFAIL, to print all test case that failed or passed, UNRESOLVED test case results are not displayed by default.
  --progress {silent,normal,no_flush_progress}
                        set progress type, silent: Don't show progress, normal: one line progress bar, update per second,no_flush_progress: print test progress per 10 seconds
  --split SPLIT         Split cases into <num> testlist
  --run_split RUN_SPLIT
                        '<A>/<B>' Split cases into <B> testlist and run part<A>

Test Suite arguments:
  test_paths            Test suite path
  --test_cfg <TEST_CFG_FILE>
                        test suite config file, needed when run a single case or with --test_list
  --test_list <TEST_LIST_FILE>
                        testlist path for filter test cases
  -C key=value, --config key=value
                        Add 'key' = 'val' to the user defined configs
  -E key=value, --env key=value
                        Add 'key' = 'val' to the user defined environment variable
  --check <CHECK_TEST_CASE>
                        testlist path for filter test cases

Running arguments:
  --temp_dir <TEMP_DIR_PATH>
                        Location for test execute.
  --directory_list <DIRECTORY_LIST_PATH>
                        Write or read a corresponding list of test execution locations and actual paths of test cases,when compatible equals False, write the list, otherwise, read the list.
  --timeout TIMEOUT     test case timeout
  --directory_structure {tile,normal}
                        set temp directory structure type, tile: Tile the temp directory, normal: set the temp directory according to the use case directory structure

Log arguments:
  --log_dir <LOG_DIR_FILE_PATH>
                        Where to store test log
  --log_level LOG_LEVEL, -l LOG_LEVEL
                        set log level from: CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET
  --verbose             enable verbose output
  --fail-verbose        enable not pass testcase verbose output
```

## `testsuites/HLT` 测试套

`testsuites/HLT` 测试套是基于 `Cangjie` 测试用例的测试套。

### `testsuites/HLT` 测试套目录结构

```shell
cangjie_test/testsuites/HLT
|--API         # API用例
|--Runtime     # 运行时用例
|--Tools       # 命令行工具用例
|--compiler    # 编译器用例
|--configs     # 配置文件
`--testlist    # 用例运行列表
```

### 测试套的测试列表

对于测试套内所有的测试列表，其中有两个部分，如下所示：

```ini
[ALL-TEST-CASE]
    API
    Runtime
    Tools
    compiler

[EXCLUDE-TEST-CASE]
    issue*
```

`[ALL-TEST-CASE]`节限定了所有可能的测试用例路径，上述测试列表指定搜索文件夹子目录下的所有测试用例。

`[EXCLUDE-TEST-CASE]`节限定了所有需要排除的用例，上述测试列表指定排除所有以issue开头的文件或文件夹下的所有测试用例。

最终的测试用例列表是，`[ALL-TEST-CASE]` 字段限定的用例文件减去 `[EXCLUDE-TEST-CASE]` 限定的用例文件。

* testsuites测试套测试用例测试列表：`cangjie_test/testsuites/HLT/testlist`
* testsuites测试套测试用例屏蔽列表：`cangjie_test/testsuites/HLT/configs/cjnative/exclude_cjnative`

```shell
python3 cangjie_test_framework/main.py --test_cfg=cangjie_test/testsuites/HLT/configs/cjnative/cangjie2cjnative_linux_x86_test.cfg --test_list=cangjie_test/testsuites/HLT/testlist,cangjie_test/testsuites/HLT/configs/cjnative/exclude_cjnative -pFAIL -j20 --timeout=180 cangjie_test/testsuites/HLT/
```

### `testsuites/HLT` 测试套配置文件说明

```shell
cangjie_test/testsuites/HLT/configs/cjnative/
|-- cangjie2cjnative_linux_arm_test.cfg       # Linux AArch64 配置文件
|-- cangjie2cjnative_linux_arm_test_O2.cfg    # Linux AArch64 配置文件，-O2
|-- cangjie2cjnative_linux_arm_test_g.cfg     # Linux AArch64 配置文件，-g
|-- cangjie2cjnative_linux_x86_test.cfg       # Linux x86_64 配置文件
|-- cangjie2cjnative_linux_x86_test_O2.cfg    # Linux x86_64 配置文件，-O2
|-- cangjie2cjnative_linux_x86_test_g.cfg     # Linux x86_64 配置文件，-g
|-- cangjie2cjnative_mac_arm_test.cfg         # macOS AArch64 配置文件
|-- cangjie2cjnative_mac_x86_test.cfg         # macOS x86_64 配置文件
`-- cangjie2cjnative_win_test.cfg             # Windows x86_64 配置文件
```

### 配置文件内容说明

#### `suffix` 说明

```ini
[suffix]
  cj = //
```

* 测试用例以`cj`作为文件后缀
* 文件后缀`cj`的测试用例内以`//`作为注释符

#### 内部变量说明

```ini
[internal-var]
  compiler = cjc
```

* 所有测试用例中的EXEC语句内的 `%compiler` 会被替换为 `cjc`
* 如果涉及脚本的运行路径需要填写绝对路径或者在环境变量 `PATH` 中，例如配置文件中：如果 `compiler` 在 `PATH` 中，则 `compiler = cjc` 即可，如果不在则 `compiler = ${CANGJIE_HOME}/bin/cjc`

### 测试框架内置变量说明

* `%f`：表示当前文件名
* `%n`：表示当前文件名去掉后缀，常用于拼接，如 `test.cj` 中可以书写 `%n.o` 表示 `test.o`
* `compare`：表示调用`cangjie_test_framework/maple_test/compare.py`，该脚本需要读取一个文件并从 `stdin` 接受输入，会解析文件中的比较关键字与 `pattern` 信息，对 `stdin` 进行比较。比较成功返回0，比较失败返回1

### 测试框架内置命令说明

#### `EXEC` 命令说明

以注释符号和 `EXEC` 起头，是测试框架的一个关键字，如果用例文件中存在该关键字认定为一个有效的测试用例，如果不存在则该文件被认定为一个辅助文件。

* `EXEC(-PIPE)(-NUM): <my_cmd>`：表示执行 `my_cmd` 命令，其中 `(-PIPE)` 和 `(-NUM)` 表示可选内容，可单独出现，也可一起出现
* `EXEC-NUM: <my_cmd>`：为了可以控制所有命令的预期 `exit code`，我们支持了 `-NUM` 选项来控制命令整体的 `exit code`。-NUM的缺省默认值为0，可以自己指定一个整数值（负数溢出需要写溢出后的正数）
* `EXEC-PIPE-NUM: <my_cmd>`：`-PIPE` 代表命令 `my_cmd` 中包含管道符 `|`，需要测试框架介入对管道符前面的命令 `exit code` 进行 `check`。`-NUM` 的功能和 `EXEC-NUM` 中的用法略有区别，此时会检查的是管道符 `|` 前命令的 `exit code`，命令整体的 `exit code` 则仍然要求为0，`-NUM` 的缺省默认值仍然为0
* `RUN-EXEC: <my_cmd>`：配置文件中若存在 `[run] script = my_script` 会自动拼接命令为：`<my_script> "my_cmd"`

#### `ERRCHECK` 命令说明

`ERRCHECK: <my_cmd>` 命令等价于 `EXEC-PIPE-1: <my_cmd> 2>&1 | compare %f`

#### `DEPENDENCE` 命令说明

指定依赖文件，测试框架在环境准备阶段会拷贝其中指定的依赖文件到临时的运行路径，如果指定依赖文件不存在，测试用例会认定失败。

#### `ASSERT` 命令说明

该关键字为可选关键字，在结果匹配与校验阶段起作用。

* `ASSERT: scan pattern`：`scan`关键字代表匹配模式为文本匹配，代表需要在输入的内容中以文本匹配 `pattern`，如果匹配成功，该语句命令以0作为退出码
* `ASSERT: regex pattern`：`regex`关键字代表匹配模式为正则匹配，代表需要在输入的内容中以正则匹配 `pattern`，如果匹配成功，该语句命令以0作为退出码

### 测试框架条件执行说明

本测试框架支持基于条件标签的测试用例执行控制。通过在测试用例的注释指令前添加条件表达式，可以根据运行时条件动态决定是否执行特定的测试命令。其基本语法为：

```shell
// (条件表达式) 测试框架内置命令: 命令内容
```

运行时条件的来源分为两类：
1. `main.py`通过`--test_cfg`选项所指定的cfg配置文件中的`[condition]`配置项，多个标签之间以一个或多个连续空白符分隔。
2. `main.py`通过`--condition`选项所指定，多个标签之间以逗号分隔。

#### 条件表达式的基本规则

- 支持逻辑运算符与括号，其中逻辑运算符可以是符号 `&` `|` `!`，也可以是对应英语单词 `and` `or` `not`。
- 标识符支持任何以字母（包括大小写）、数字、下划线组成的字符串，如 `debug_mode`、`001`、`IMPORTANT`等。
- 条件表达式中的空白符均将被忽略。

### 测试用例运行校验

1. 测试用例中的执行语句返回值
2. 匹配测试用例运行的输出：通过 `compare` 脚本进行结果匹配，如果匹配成功，则 `compare` 脚本退出码为 0，匹配失败则退出码为非 0

`cangjie_test_framework/maple_test/compare.py`

```shell
usage: compare.py [-h] [--comment COMMENT] [--assert_flag ASSERT_FLAG] [--expected_flag EXPECTED_FLAG] [--condition [CONDITION]] [--compare_object [COMPARE_OBJECT]] [--transfer TRANSFER] case_path[com_opt]

positional arguments:
  case_path             Source path:read compare rules
  com_opt               Compile option of this case, default empty.
  
 options:
  -h, --help            show this help message and exit
  --comment COMMENT    Test case comment
  --assert_flag ASSERT_FLAG
                        Test case assert flag, default ASSERT 
  --expected_flag EXPECTED_FLAG
                        Test case expected flag for compile, default EXCEPTED
  --condition [CONDITION]
                        Compare condition for Keyword, default empty. 
  --compare_object [COMPARE_OBJECT]
                        compare object, default stdin
  --transfer TRANSFER   Base dir for transfer/update normal case to multiline case.
```

### 测试用例说明

`cangjie_test/testsuites/HLT/compiler/cjnative/Chir/ForIn/for_in_01.cj`

```cangjie
/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
 * This source file is part of the Cangjie project, licensed under Apache-2.0
 * with Runtime Library Exception.
 *
 * See https://cangjie-lang.cn/pages/LICENSE for license information.
*/

// LEVEL: 2
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt % output %run_args

func test() {
    var a = "HELLO"
    var b: UInt8 = 0
    for (i in a where Int64(i) == 72) {
        b += i 
        if (Int64(b) == 72) {
            break        
        }
    }
    return b
}

main() {
    if (Int64(test()) == 72) {
        return 0
    } else {
        return 1
    }
    return 1
}
```

#### 测试用例测试代码部分

```cangjie
func test() {
    var a = "HELLO"
    var b: UInt8 = 0
    for (i in a where Int64(i) == 72) {
        b += i 
        if (Int64(b) == 72) {
            break        
        }
    }
    return b
}

main() {
    if (Int64(test()) == 72) {
        return 0
    } else {
        return 1
    }
    return 1
}
```

#### 测试用例运行部分

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args
```

两条执行语句：

1. EXEC语句，利用 `%compiler`，采用 `%cmp_opt` 编译选项，编译测试用例 `%f` 为 `%output`
2. RUN-EXEC语句，运行编译产物 `%output`

## `ASSERT` 的详细使用方法

`compare.py` 是一个用于验证程序输出结果的测试框架工具。它通过解析测试用例文件中的 `// ASSERT:` 注释行，对程序的输出进行字符串或正则表达式匹配。`ASSERT` 的基本语法如下：

```cangjie
// ASSERT: <模式类型> [关键词] <匹配内容>
```

其中：

- 模式类型：`scan` 或 `regex`
- 关键词：可选，用于修饰匹配行为
- 匹配内容：要匹配的字符串或正则表达式

以下是一个所有断言均成功的使用案例：

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-begin Starting test
// ASSERT: scan-next Step 1
// ASSERT: scan-after OK
// ASSERT: scan-next Step 2
// ASSERT: scan-3 OK
// ASSERT: regex-not (fail|error)
// ASSERT: scan-begin All checks
// ASSERT: scan-after passed
// ASSERT: scan-end

main(): Unit {
    println("Starting test")
    println("Step 1")
    println("OK")
    println("Step 2")
    println("OK")
    println("Final OK")
    println("Test completed successfully")
    println("All checks passed")
}
```

下表列举了所有支持的模式类型和关键词组合的场景：

|方法 | 类型 | 关键词 | 功能描述 |
|---|-----|-------|----------|
|scan | scan | 无 | 基础包含匹配 |
|scan-not | scan | not | 否定匹配 |
|scan-full | scan | full | 完全匹配 |
|scan-begin | scan | begin | 从头开始匹配 |
|scan-next | scan | next | 从下一行匹配 |
|scan-after | scan | after | 从之后匹配 |
|scan-end | scan | end | 检查末尾 |
|scan-N | scan | 数字 | 精确次数匹配 |
|scan-txt | scan | txt | 文本模式（Windows） |
|regex | regex | 无 | 基础正则匹配 |
|regex-not | regex | not | 正则否定匹配 |
|regex-full | regex | full | 正则完全匹配 |
|regex-begin | regex | begin | 从头开始正则匹配 |
|regex-next | regex | next | 从下一行正则匹配 |
|regex-after | regex | after | 从之后正则匹配 |
|regex-end | regex | end | 检查末尾 |
|regex-auto | regex | auto | 自动正则匹配 |
|regex-N | regex | 数字 | 精确次数正则匹配 |

二、scan模式（字符串匹配）
1. scan— 基础包含匹配
检查输出中包含指定字符串。

// ASSERT: scan Hello World

    匹配方式：content.find(pattern) != -1
    成功条件：输出中任意位置包含 "Hello World"
    默认起始位置：从输出开头开始搜索

2. scan not— 否定匹配
检查输出中不包含指定字符串。

// ASSERT: scan not Error

    匹配方式：对 scan结果取反
    成功条件：输出中不包含 "Error"

3. scan full— 完全匹配
检查输出完全等于指定字符串。

// ASSERT: scan full Hello World

    匹配方式：content != pattern
    成功条件：输出内容与 "Hello World" 完全一致
    注意：会进行 Unicode 转义处理

4. scan begin— 从头开始匹配
从输出开头开始搜索。

// ASSERT: scan begin Hello

    匹配方式：从位置 0 开始调用 scan_match
    成功条件：输出开头包含 "Hello"
    影响：会重置后续 next/after的起始位置

5. scan next— 从下一行匹配
从上一次匹配位置的下一行开始搜索。

// ASSERT: scan begin Start
// ASSERT: scan next Middle
// ASSERT: scan next End

    匹配方式：在 content.splitlines()[line_num]中搜索
    成功条件：在指定行中找到模式
    前置要求：必须先使用 begin

6. scan after— 从之后匹配
从上一次匹配位置之后开始搜索。

// ASSERT: scan begin Start
// ASSERT: scan after End

    匹配方式：在 '\n'.join(content.splitlines()[line_num:])中搜索
    成功条件：在 "Start" 之后的位置找到 "End"
    前置要求：必须先使用 begin

7. scan end— 检查末尾
检查是否已经到达输出末尾。

// ASSERT: scan begin Content
// ASSERT: scan end

    匹配方式：检查 line_num < len(line_map)
    成功条件：当前行号超出输出总行数

8. scan-N— 精确次数匹配
检查指定字符串恰好出现 N 次。

// ASSERT: scan-3 Hello

    匹配方式：content.count(pattern) != count
    成功条件："Hello" 恰好出现 3 次
    支持：scan not-3（不恰好出现 N 次）

9. scan txt— 文本模式（Windows 路径）
用于 Windows 路径匹配，自动处理路径分隔符。

// ASSERT: scan txt C:\path\to\file

    匹配方式：在 Windows 上不进行路径转换
    成功条件：输出包含指定路径

三、regex模式（正则表达式匹配）
1. regex— 基础正则匹配
检查输出匹配指定正则表达式。

// ASSERT: regex Error code: \d+

    匹配方式：re.finditer(pattern, content, re.MULTILINE)
    成功条件：输出中存在至少一处匹配
    支持命名分组：匹配结果会存入 global_group_dict，可在后续断言中通过 (?P=name)引用

2. regex not— 正则否定匹配
检查输出不匹配指定正则表达式。

// ASSERT: regex not (fail|error|warning)

    匹配方式：对 regex_match结果取反
    成功条件：输出中不匹配正则

3. regex full— 正则完全匹配
检查输出完全匹配指定正则表达式。

// ASSERT: regex full Hello World

    匹配方式：content != pattern
    成功条件：输出与正则完全一致

4. regex begin— 从头开始正则匹配
从输出开头开始正则搜索。

// ASSERT: regex begin Hello

    匹配方式：从位置 0 开始调用 regex_match
    成功条件：输出开头匹配正则

5. regex next— 从下一行正则匹配
从上一次匹配位置的下一行开始正则搜索。

// ASSERT: regex begin Start
// ASSERT: regex next Middle
// ASSERT: regex next End

    匹配方式：在 content.splitlines()[line_num]中搜索
    前置要求：必须先使用 begin

6. regex after— 从之后正则匹配
从上一次匹配位置之后开始正则搜索。

// ASSERT: regex begin Start
// ASSERT: regex after End

    匹配方式：在 '\n'.join(content.splitlines()[line_num:])中搜索
    前置要求：必须先使用 begin

7. regex end— 检查末尾（正则模式）
检查是否已经到达输出末尾。

// ASSERT: regex begin Content
// ASSERT: regex end

    匹配方式：同 scan end

8. regex auto— 自动正则匹配
自动将空格分隔的单词转换为正则表达式。

// ASSERT: regex auto Hello World

    匹配方式：r"\s+".join([re.escape(word) for word in pattern.split()])
    成功条件：输出中 "Hello" 和 "World" 之间可以有任意空白

9. regex-N— 精确次数正则匹配
检查正则表达式恰好匹配 N 次。

// ASSERT: regex-3 \d{3}

    匹配方式：len(re.findall(pattern, content)) != count
    成功条件：三位数字恰好出现 3 次
