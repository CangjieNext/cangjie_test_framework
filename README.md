# Maple Test Framework

This project's test framework is the open-source test framework for the OpenArkCompiler: https://gitee.com/openarkcompiler/OpenArkCompiler/tree/master/test

## Directory Structure

```shell
cangjie_test_framework/
|-- README.md           # Test framework description
|-- main.py             # Entry point for running test suites
`-- maple_test          # Test framework source code
   |--__init__.py
   |--compare.py        # Result verification module
   |--configs.py        # Configuration and parameter module
   |--main.py           # Internal entry
   |--maple_test.cfg    # Test framework configuration file
   |--run.py            # Command execution module
   |--task.py           # Test task preparation and execution module
   |--template.cfg      # Test-suite configuration file template
   |--test.py           # Test-case module
   `--utils.py          # Common utilities
```

## Requirements

* `python` Version >= 3.5.2

## Modify Framework Configuration

File: `maple_test.cfg`

```ini
# Test framework configuration file. Currently only supports configuring test-suite paths, temporary run-time directories, and log storage via this file.
[test-home]
# ':' list of test-suite directories
dir = 
    ../../cangjie_test/testsuites/HLT:../../cangjie_test/testsuites/LLT

[running]
# Temporary directory used during test execution
temp_dir = ../test_temp/run

[logging]
# Directory for saving test logs
name = ../test_temp/log
level = INFO
```

## Execution Instructions

Test-case execution depends:

* Cangjie SDK:[Install Cangjie SDK](https://gitcode.com/Cangjie/cangjie_docs/blob/main/docs/dev-guide/source_zh_cn/first_understanding/install.md)
* `Git Bash`: Add to the `Path` environment variable
* `Python` packages: `pexpect` and `fasteners` modules
* `OpenSSL 3`: Dynamic libraries `ssl` and `crypto`
* `JDK`
* `llvm-15.0.4`
* `MinGW-w64`

Download test cases:

```shell
git clone https://gitcode.com/Cangjie/cangjie_test.git
```

Download test framework:

```shell
git clone https://gitcode.com/Cangjie/cangjie_test_framework.git
```

All the examples below are executed on a `Linux x86_64` host. If you need to run them in a different environment, please select the appropriate configuration file for that target.

### Run A Single `testsuites/HLT` Case

```shell
python3 cangjie_test_framework/main.py --test_cfg=cangjie_test/testsuites/HLT/configs/cjnative/cangjie2cjnative_linux_x86_test.cfg --verbose cangjie_test/testsuites/HLT/compiler/cjnative/Chir/ForIn/for_in_01.cj
```

### Run A Single `testsuites/HLT/Tools/cjlsp` Case

Run `LSP` case, you need to copy the `modules` directory from the `${CANGJIE_HOME}` to the `tools/bin` path:

```shell
cp -r ${CANGJIE_HOME}/modules ${CANGJIE_HOME}/tools/bin
```

Modify the `lsp_server` path in the configuration file `cangjie_test/testsuites/HLT/Tools/cjlsp/lsp_config.txt` by replacing the placeholder with the absolute path of `${CANGJIE_HOME}/tools/bin`:

```ini
[lsp_server]
    win_path = ${win_lsp_server_path} 	   // Modify this line for Windows environment
    linux_path = ${linux_lsp_server_path}  // Modify this line for Linux or MAC environment
```

The remaining execution steps are the same as those for other test cases.

### Run All Cases In `testsuites/HLT`

```shell
python3 cangjie_test_framework/main.py --test_cfg=cangjie_test/testsuites/HLT/configs/cjnative/cangjie2cjnative_linux_x86_test.cfg --test_list=cangjie_test/testsuites/HLT/testlist -pFAIL -j20 --timeout=180 cangjie_test/testsuites/HLT/ 
```

### Run All The Configured Test Suites

Prepare the default test suite configuration files.

```shell
cp cangjie_test/testsuites/HLT/configs/cjnative/cangjie2cjnative_linux_x86_test.cfg cangjie_test/testsuites/HLT/test.cfg
cp cangjie_test/testsuites/LLT/configs/cjnative/cjnative_test.cfg cangjie_test/testsuites/LLT/test.cfg
```

Update the `root` paths in the following configuration files:

* `cangjie_test/testsuites/HLT/test.cfg`
* `cangjie_test/testsuites/LLT/test.cfg`

```ini
[root]
  path = ./
```

Run both `testsuites/HLT` and `testsuites/LLT` together:

```shell
python3 cangjie_test_framework/main.py -pFAIL -j20 --timeout=180
```

Parameter Description: Specifies a parameter to overwrite the settings in the framework configuration file.

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

## `testsuites/HLT` Test Suite

`testsuites/HLT` The test suite is based on `Cangjie` test cases.

### Directory Structure Of `testsuites/HLT`

```shell
cangjie_test/testsuites/HLT
|--API         # API tests
|--Runtime     # Runtime tests
|--Tools       # Tools tests
|--compiler    # Compiler tests
|--configs     # Configuration files
`--testlist    # Test-case run list
```

### Test-Case Lists

Each test lists within the test suite contains two sections:

```ini
[ALL-TEST-CASE]
    API
    Runtime
    Tools
    compiler

[EXCLUDE-TEST-CASE]
    issue*
```

`[ALL-TEST-CASE]` lists all directories to be searched for test cases.

`[EXCLUDE-TEST-CASE]` lists patterns to exclude (e.g., anything starting with issue).

The final test list = [ALL-TEST-CASE] - [EXCLUDE-TEST-CASE].

* Test-case inclusion list: `cangjie_test/testsuites/HLT/testlist`
* Test-case exclusion list: `cangjie_test/testsuites/HLT/configs/cjnative/exclude_cjnative`.

```shell
python3 cangjie_test_framework/main.py --test_cfg=cangjie_test/testsuites/HLT/configs/cjnative/cangjie2cjnative_linux_x86_test.cfg --test_list=cangjie_test/testsuites/HLT/testlist,cangjie_test/testsuites/HLT/configs/cjnative/exclude_cjnative -pFAIL -j20 --timeout=180 cangjie_test/testsuites/HLT/
```

### Configuration Files Of `testsuites/HLT`

```shell
cangjie_test/testsuites/HLT/configs/cjnative/
|-- cangjie2cjnative_linux_arm_test.cfg       # Linux AArch64 config
|-- cangjie2cjnative_linux_arm_test_O2.cfg    # Linux AArch64, -O2
|-- cangjie2cjnative_linux_arm_test_g.cfg     # Linux AArch64, -g
|-- cangjie2cjnative_linux_x86_test.cfg       # Linux x86_64 config
|-- cangjie2cjnative_linux_x86_test_O2.cfg    # Linux x86_64, -O2
|-- cangjie2cjnative_linux_x86_test_g.cfg     # Linux x86_64, -g
|-- cangjie2cjnative_mac_arm_test.cfg         # macOS AArch64 config
|-- cangjie2cjnative_mac_x86_test.cfg         # macOS x86_64 config
`-- cangjie2cjnative_win_test.cfg             # Windows x86_64 config
```

### Configuration File Descriptions

#### `suffix` Section

```ini
[suffix]
  cj = //
```

* Test-case file extension: `cj`
* Comment symbol inside `cj` files: `//`

#### Internal Variables

```ini
[internal-var]
  compiler = cjc
```

* All occurrences of `%compiler` in test cases are replaced with `cjc`.
* If the script is not in `PATH`, use an absolute path (e.g.,`compiler = ${CANGJIE_HOME}/bin/cjc`)

### Built-in Variables Of The Test Framework  

* `%f`: current file name
* `%n`: file name without extension (e.g., for `test.cj`, `%n.o` becomes `test.o`)
* `compare`: invokes `cangjie_test_framework/maple_test/compare.py`. The script reads a rule file and compares stdin against expected patterns; returns 0 on match, 1 otherwise.

### Built-in Commands

#### `EXEC` Command

Lines starting with the comment marker followed by `EXEC` are recognized as valid test cases; files without such lines are treated as auxiliary.

* `EXEC(-PIPE)(-NUM): <my_cmd>`: Executes `my_cmd`. Optional `-PIPE` and `-NUM` can appear alone or together.
* `EXEC-NUM: <my_cmd>`: Sets the expected exit code of the command to `NUM` (default 0).
* `EXEC-PIPE-NUM: <my_cmd>`: `-PIPE` indicates the command contains `|`, and the framework checks the exit code before the pipe. The overall exit code must still be 0 unless overridden.
* `RUN-EXEC: <my_cmd>`: If `[run] script = my_script` exists in the config, the framework forms `<my_script> "my_cmd"`

#### `ERRCHECK` Command

`ERRCHECK: <my_cmd>` is equivalent to `EXEC-PIPE-1: <my_cmd> 2>&1 | compare %f`.

#### `DEPENDENCE` Command

Lists dependency files. The framework copies them to the temporary run directory before execution; missing dependencies cause the case to fail.

#### `ASSERT` Command

Optional keyword used during result verification.

* `ASSERT: scan pattern` - literal text match.
* `ASSERT: regex pattern` - regex match.

### Conditional Execution

This test framework supports conditional execution control of test cases based on conditional tags. By adding conditional expressions before comment directives in test cases, you can dynamically determine whether to execute specific test commands based on runtime conditions. The basic syntax is:

```shell
// (conditional_expression) builtin_command: command_content
```

The sources of runtime conditions are divided into two categories:

1. The `[condition]` field in the cfg configuration file specified by `--test_cfg` option when running `main.py`, where multiple tags are separated by one or more consecutive whitespaces.

2. The tags specified by the `--condition` option when running main.py, where multiple tags are separated by commas.

#### Basic Rules for Conditional Expressions

- Supports logical operators and parentheses. Logical operators can be symbols `&`, `|`, `!`, or their corresponding English words `and`, `or`, `not`.
- Identifiers support any string composed of letters (both uppercase and lowercase), numbers, and underscores, such as `debug_mode`, `001`, `IMPORTANT`, etc.
- All whitespace characters in conditional expressions will be ignored.

### Test-Case Validation

* Exit code of executed commands
* Output matching via `compare` script; exit code 0 means success.

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
                        Test case expected flag for compile, default EXPECTED
  --condition [CONDITION]
                        Compare condition for Keyword, default empty. 
  --compare_object [COMPARE_OBJECT]
                        compare object, default stdin
  --transfer TRANSFER   Base dir for transfer/update normal case to multiline case.
```

### Test-Case Example

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
// RUN-EXEC: %run %run_opt %output %run_args

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

#### Test-Case Code Section

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

#### Test-Case Execution Section

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args
```

Two execution statements:

1. EXEC statement: uses `%compiler` with `%cmp_opt` to compile the test case `%f` into `%output`.
2. RUN-EXEC statement: runs the compiled output `%output`.

## Detailed Usage of ASSERT

`compare.py` is a built-in tool of the testing framework used to verify program output. It parses `// ASSERT:` comment lines in specified files to perform string or regular expression matching against the program's output. The basic syntax of ASSERT is as follows:

```cangjie
// ASSERT: <mode_type>[-keyword] <match_content>
```

The three components are:

- Mode Type: scan or regex, indicating string matching or regular expression matching respectively.
- Keyword: Optional, used to further specify the matching behavior.
- Match Content: The string or regular expression to match against.

For example, all of the following assertions will succeed:

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

The table below lists all supported mode types and keyword combinations. Some keywords can be combined:

| Method | Description |
| ------ | ----------- |
| `scan` | Checks if the output contains the specified string. |
| `scan-not` | Checks if the output does NOT contain the specified string. |
| `scan-full` | Checks if the output exactly matches the specified string. |
| `scan-begin` | Same as `scan`, but resets the search start position for subsequent `scan-next` and `scan-after` calls. |
| `scan-next` | Searches on the line immediately following the position of the last successful `scan-begin` match. |
| `scan-after` | Searches starting from the character immediately after the position of the last successful `scan-begin` match. |
| `scan-end` | Checks if the current search start position has reached the end of the output. |
| `scan-N` | Checks if the specified string appears exactly `N` times in the output. |
| `regex` | Checks if the specified regular expression successfully matches the output. |
| `regex-not` | Checks if the specified regular expression does NOT successfully match the output. |
| `regex-auto` | Same as `regex`, but simplifies the handling of whitespace in the specified regular expression. |
| `regex-N` | Checks if the specified regular expression successfully matches exactly `N` times in the output. |

### Scan Mode

#### `scan`

Always searches from the beginning of the output to check if the output contains the specified string.

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan World

main(): Unit {
    println("Hello World, My Friend!")
}
```

The above test case will succeed because the string `"World"` exists in the output.

#### `scan-not`

Always searches from the beginning of the output to check if the output does NOT contain the specified string.

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-not Bad

main(): Unit {
    println("Hello World, My Friend!")
}
```

The above test case will succeed because the string `"Bad"` does not exist in the output.

#### `scan-full`

Checks if the output exactly matches the specified string. Note that escape characters are supported in the string.

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: scan-full Hello World\nAnd Have A Good Day\n

main(): Unit {
    println("Hello World")
    println("And Have A Good Day")
}
```

The above test case will succeed because the output exactly matches `"Hello World\nAnd Have A Good Day\n"`.

#### `scan-begin`

Matches and sets the search start position. Its matching capability is the same as `scan`, but upon a successful match, it sets the search start position for the next match. It should be used in conjunction with `scan-next`, `scan-after`, and `scan-end`.

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

All assertions in the above test case will succeed. `scan-begin Hello` searches from the beginning of the output and matches `"Hello"` on the second line. This sets the search start position for the next match to the first character after `"Hello"`, which is `"W"`. The subsequent `scan-after World` then matches successfully. After `scan-begin End` matches successfully, it again sets the search start position for the next match to the character after `"End"`, which is the newline character. The subsequent `scan-next` starts searching from the next line, but since it matches an empty string, it also succeeds. Finally, `scan-end` successfully matches the end of the output.

#### `scan-next`

Matches on the line immediately following the current search start position (determined by the previous `scan-begin`).

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

In the above test case, `scan-next World` will fail. Because after `scan-begin Hello` succeeds, the search start position for the next match is on the line containing `"Hello"`. `scan-next World` will only search on the next line, which is the line containing `"Goodbye"`, and thus will not find `"World"`, causing the assertion to fail.

Modifying the above test case as follows will cause all assertions to succeed:

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

Starts searching for a match from the current search start position (determined by the previous `scan-begin`).

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

The above test case will fail. `scan-after Hello` will fail because after `scan-begin Goodbye` succeeds, `"Hello"` does not exist after the search start position.

Modifying the above test case as follows will cause all assertions to succeed:

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

Alternatively, changing `scan-after` to `scan` will also work:

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

Checks if the current search start position has reached the end of the output. If it has reached the end, the assertion succeeds; otherwise, it fails.

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

The above test case will fail. `scan-end` will fail because after `scan-after Goodbye` succeeds, the search start position has not yet reached the end of the output.

Modifying the above test case as follows will cause it to succeed:

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

Exact count matching. Checks if the specified string appears exactly `N` times. The assertion fails if the number of occurrences is not equal to `N`.

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

The above test case will succeed because the string `"Good"` appears exactly 3 times.

### regex Mode

Regular expression matching.

#### `regex`

Basic regular expression matching. Checks if the output contains at least one match for the regular expression. Always attempts to match from the beginning of the output.

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: regex My #\d+ Friend

main(): Unit {
    println("Hello World, My #100 Friend!")
}
```

The above test case will succeed because the output contains `"My #100 Friend"`, which matches the regular expression.

#### `regex-not`

Negative regular expression matching. Checks if the output completely fails to match the specified regular expression. Always attempts to match from the beginning of the output.

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: regex-not (Fail|Error|Warning)

main(): Unit {
    println("Success")
}
```

The above test case will succeed because the output contains none of `"Fail"`, `"Error"`, or `"Warning"`.

#### `regex-auto`

Simplifies the handling of whitespace characters in user-written regular expressions, building upon standard regular expression matching.

```cangjie
// EXEC: %compiler %cmp_opt %f -o %output
// RUN-EXEC: %run %run_opt %output %run_args | compare %f
// ASSERT: regex-auto Nice to  meet   you
// ASSERT: regex Nice to  meet   you

main(): Unit {
    println("Nice   to  meet you~")
}
```

In the above test case, `regex-auto` will succeed, while `regex` will fail. This is because `regex` performs matching strictly according to the given regular expression string (treating spaces literally), whereas `regex-auto` automatically replaces sequences of whitespace with `\s+`, allowing it to successfully match the output.

#### `regex-N`

Exact count regular expression matching. Checks if the specified regular expression successfully matches exactly `N` times. The assertion fails if the number of matches is not equal to `N`.

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

The above test case will succeed because the regular expression matches exactly 10 times.
