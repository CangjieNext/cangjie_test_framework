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

`compare.py` 是用于验证程序输出结果的测试框架内置工具，它通过解析指定文件中的 `// ASSERT:` 注释行，对程序的输出内容进行字符串或正则表达式匹配。`ASSERT` 的基本语法如下：

```cangjie
// ASSERT: <模式类型>[-关键词] <匹配内容>
```

其中的三个组成部分：

- 模式类型：`scan` 或 `regex`，分别表示字符串匹配和正则表达式匹配
- 关键词：可选，用于进一步确定匹配行为
- 匹配内容：要匹配的字符串或正则表达式

举个例子，以下所有断言均将成功：

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

下表中列举了所有支持的模式类型和关键词组合的场景，其中部分关键词可以叠加组合：

| 方法 | 功能描述 |
| ---- | ---------|
| `scan` | 检查输出中是否包含指定的字符串 |
| `scan-not` | 检查输出中是否不包含指定的字符串 |
| `scan-full` | 检查输出是否与指定的字符串完全一致 |
| `scan-begin` | 同 `scan`，但将重置后续 `scan-next`、`scan-after` 的搜索起始位置 |
| `scan-next` | 在上一次 `scan-begin` 匹配成功的位置的下一行中进行搜索 |
| `scan-after` | 从上一次 `scan-begin` 匹配成功的位置的下一个字符开始搜索 |
| `scan-end` | 检查当前的搜索起始位置是否已经到达输出内容的末尾 |
| `scan-N` | 检查指定的字符串是否在输出中恰好出现 `N` 次 |
| `regex` | 检查指定的正则表达式是否能够成功匹配输出内容 |
| `regex-not` | 检查指定的正则表达式是否并不能成功匹配输出内容 |
| `regex-auto` | 同 `regex`，但将简化指定的正则表达式中空格的处理 |
| `regex-N` |  检查指定的正则表达式是否在输出内容中恰好成功匹配 `N` 次 |

### scan 模式

#### `scan`

总是从输出的开头开始搜索，检查输出中是否包含指定的字符串。

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan World

main(): Unit {
    println("Hello World, My Friend!")
}
```

以上用例将成功，因为输出中存在字符串 `"World"`。

#### `scan-not`

总是从输出的开头开始搜索，检查输出中是否不包含指定的字符串。

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-not Bad

main(): Unit {
    println("Hello World, My Friend!")
}
```

以上用例将成功，因为输出中不存在字符串 `"Bad"`。

#### `scan-full`

检查输出是否与指定的字符串完全一致。注意，字符串中支持转义字符。

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-full Hello World\nAnd Have A Good Day\n

main(): Unit {
    println("Hello World")
    println("And Have A Good Day")
}
```

以上用例将成功，因为输出的内容与 `"Hello World\nAnd Have A Good Day\n"` 完全一致。

#### `scan-begin`

匹配并设置搜索起始位置。匹配能力同 `scan`，但匹配成功后将设置下一次匹配时的搜索起始位置，应与 `scan-next`、`scan-after` 和 `scan-end` 配合使用。

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-begin Hello
// ASSERT: scan-after World
// ASSERT: scan-next EveryOne
// ASSERT: scan-begin End
// ASSERT: scan-next
// ASSERT: scan-end

main(): Unit {
    println("First Of All,")
    println("HelloWorld")
    println("EveryOne")
    println("End")
}
```

以上用例将全部断言成功，`scan-begin Hello` 将从输出内容的开头开始搜索，匹配到第二行的 `"Hello"`，此时将设置下一次匹配时的搜索起始位置为 `"Hello"` 之后的第一个字符 `"W"` 处，紧接着的 `scan-after World` 于是继续成功匹配。之后的 `scan-begin End` 匹配成功后，将再次设置下一次匹配时的搜索起始位置为 `"End"` 的后一个字符，即换行符，接着的 `scan-next` 从下一行开始匹配，但匹配的是空字符串，于是也能成功匹配。最后的 `scan-end` 成功匹配到输出的末尾。

#### `scan-next`

在当前搜索起始位置（由上一个 `scan-begin` 决定）的下一行中匹配。

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-begin Hello
// ASSERT: scan-next World

main(): Unit {
    println("Hello")
    println("Goodbye")
    println("World")
}
```

以上用例中 `scan-next World` 将断言失败，因为 `scan-begin Hello` 断言成功后，此时下一次搜索起始位置位于 `"Hello"` 所在行，`scan-next World` 将只在下一行，也就是 `"Goodbye"` 所在行进行搜索，故没有搜索到 `"World"`，从而导致失败。

将以上用例修改为如下用例后，所有断言均将成功：

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-begin Hello
// ASSERT: scan-next Goodbye
// ASSERT: scan-next World

main(): Unit {
    println("Hello")
    println("Goodbye")
    println("World")
}
```

#### `scan-after`

从当前搜索起始位置（由上一个 `scan-begin` 决定）开始搜索匹配。

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-begin Goodbye
// ASSERT: scan-after Hello

main(): Unit {
    println("Hello")
    println("Goodbye")
    println("AndGoodNight")
}
```

以上用例将失败，`scan-after Hello` 将断言失败，因为当 `scan-begin Goodbye` 断言成功后，搜索起始位置之后不存在 `"Hello"`。

将以上用例修改为如下用例后，所有断言均将成功：

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-begin Hello
// ASSERT: scan-after Goodbye

main(): Unit {
    println("Hello")
    println("Goodbye")
    println("AndGoodNight")
}
```

或将 `scan-after` 修改为 `scan`：

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-begin Goodbye
// ASSERT: scan Hello

main(): Unit {
    println("Hello")
    println("Goodbye")
    println("AndGoodNight")
}
```

#### `scan-end`

检查当前搜索起始位置是否已经到达输出内容的末尾，如果已经到达末尾则判定成功，否则失败。

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-begin Hello
// ASSERT: scan-after Goodbye
// ASSERT: scan-end

main(): Unit {
    println("Hello")
    println("Goodbye")
    println("AndGoodNight")
}
```

以上用例将失败，`scan-end` 将断言失败，因为 `scan-after Goodbye` 断言成功后，搜索起始位置尚未到底输出内容的末尾。

将以上用例修改为如下后将成功：

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-begin Hello
// ASSERT: scan-after Goodbye
// ASSERT: scan-after AndGoodNight
// ASSERT: scan-end

main(): Unit {
    println("Hello")
    println("Goodbye")
    println("AndGoodNight")
}
```

#### `scan-N`

精确次数匹配。检查指定字符串是否恰好出现 `N` 次，只要出现次数与 `N` 不相等即判定失败。

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-3 Good

main(): Unit {
    println("GoodMorning")
    println("Hello")
    println("Goodbye")
    println("AndGoodNight")
}
```

以上用例将成功，因为字符串 `"Good"` 恰好出现了3次。

### `regex` 模式

正则表达式匹配。

#### `regex`

基础正则表达式匹配。检查输出中是否包含至少一处正则匹配，总是从输出的开头尝试匹配。

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: regex My #\d+ Friend

main(): Unit {
    println("Hello World, My #100 Friend!")
}
```

以上用例将成功，因为输出中存在 `"My #100 Friend"` 与正则表达式匹配。

#### `regex-not`

正则否定匹配。检查输出内容完全不匹配指定的正则表达式，总是从输出的开头尝试匹配。

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: regex-not (Fail|Error|Warning)

main(): Unit {
    println("Success")
}
```

以上用例将成功，因为输出中完全不存在 `"Fail"`、`"Error"` 或 `"Warning"`。

#### `regex-auto`

在普通正则匹配的基础上，简化用户手写正则表达式中空白符。

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: regex-auto Nice to  meet   you
// ASSERT: regex Nice to  meet   you

main(): Unit {
    println("Nice   to  meet you~")
}
```

在以上用例中，`regex-auto` 将断言成功，而 `regex` 将断言失败，因为 `regex` 将按照给定的正则表达式字符串进行匹配，而 `regex-auto` 则会自动替换`\s+`，故能成功匹配输出内容。

#### `regex-N`

精确次数正则匹配。检查指定正则表达式是否恰好成功匹配 `N` 次，只要匹配次数与 `N` 不相等即判定失败。

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: regex-10 My #\d+ Friend

main(): Unit {
    println("Nice to meet you~")
    for (i in 0..10) {
        println("Hello World, My #${i} Friend!")
    }
}

```

以上用例将成功，因为正则表达式恰好成功匹配了10次。
