# BugBane

🌍 English | [**Русский**](README.ru.md)

Fuzz testing automation toolkit.<br>

# Features

BugBane goals:
1. CI fuzzing pipeline simplification by generalizing typical testing steps and standardizing the resulting artifacts.
2. Performing fuzzing in an efficient configuration based on best practices.
3. Reports generation in accordance with the actual actions performed.

BugBane features:
1. Building applications for fuzz testing with sanitizers and coverage support: AFL++, libFuzzer.
2. Fuzzing built targets with [AFL++](https://github.com/AFLplusplus/AFLplusplus), [libFuzzer](https://www.llvm.org/docs/LibFuzzer.html), [dvyukov/go-fuzz](https://github.com/dvyukov/go-fuzz), [go test](https://go.dev/security/fuzz) using a given number of CPU cores until meeting a given stop condition.
3. Synchronizing test cases between fuzzer and storage directories, including deduplication and minimization with use of fuzzer tools.
4. Coverage collection of tested app's source code using fuzzer-generated samples, coverage reports creation.
5. Reproducing of fuzzer-discovered crashes and hangs. Determining location of bugs in the source code.
6. Submitting reproducible bugs to vulnerability management system: [Defect Dojo](https://github.com/DefectDojo/django-DefectDojo).
7. Creating screenshots for both fuzzers and coverage reports.
8. Report generation with use of Jinja2 templates.

The BugBane utilities are best used together, though they're also usable on their own.

# Install

## Requirements
UNIX-like OS<br>
Python >= 3.6<br><br>
Dependencies required by the tools:<br>
**bb-build**: fuzzer compilers in PATH (afl-g++-fast, clang, ...).<br>
**bb-corpus**: fuzzer minimization tools in PATH (afl-cmin, ...).<br>
**bb-fuzz**: fuzzer binary in PATH (afl-fuzz, go-fuzz, ...).<br>
**bb-coverage**: coverage tools to be used in PATH (lcov, genhtml, go, ...).<br>
**bb-reproduce**: `timeout` utility, `gdb` debugger.<br>
**bb-send**: python library `defectdojo_api`.<br>
**bb-screenshot**, **bb-report**: python libraries `Jinja2`, `WeasyPrint`, `Selenium`, applications `ansifilter` and `pango-view` in PATH, `geckodriver` in PATH and Firefox web browser (optional, only for Selenium functionality), any `mono` fonts (may be missing in Docker images).<br>
Notes:
- Python libraries are installed automatically along with BugBane;
- screenshots of coverage reports look better when created with Selenium rather than with WeasyPrint, though Selenium requires Firefox and geckodriver;
- Go coverage reports require Selenium to create screenshots, because Go coverage reports heavily rely on JavaScript;
- in order to view reports in docker container with utils like `less` it may be required to generate a locale with UTF-8 support and to set the LANG env variable.

## Installing and uninstalling the package
To install BugBane clone its repo and use pip:
```
git clone https://github.com/gardatech/bugbane
cd bugbane
pip install .[all]
```
Make sure all tests pass:
```
pytest
```

<details>
<summary>Additional setup instructions</summary>

There are install groups available other than "all", which allow smaller installations with only required Python dependencies:
| pip install group | Fuzzing\* | Submitting bugs to Defect Dojo | Reports and screenshots | BugBane testing | BugBane development |
|-|-|-|-|-|-|
| - | + | - | - | - | - |
| dd | + | + | - | - | - |
| reporting | + | - | + | - | - |
| test | + | - | - | + | - |
| all | + | + | + | + | - |
| dev | + | + | + | + | + |

\* Performing builds, fuzz testing, corpus syncing, coverage collection, and bug reproducing.

Thus, it's possible to separate fuzz testing and working with its results to different hosts, for instance, `worker` and `reporter`:
```shell
pip install .                  # worker
pip install .[dd,reporting]    # reporter
```
As a result, the `worker` host doesn't need report generation dependencies, and the `reporter` host doesn't need an environment to run tested applications or fuzzers.

To uninstall BugBane use the following command:
```
pip uninstall bugbane
```

</details>

# How to use
It is recommended to use BugBane in a Docker environment.<br>
Sequential use of the tools is implied, for example:
1. bb-build
2. bb-corpus (import)
3. bb-fuzz
4. bb-coverage
5. bb-reproduce
6. bb-corpus (export)
7. bb-send
8. bb-report

However, step #1 is optional, as builds can be done by other means, and steps #7 and #8 can be performed in a separate Docker image or on a separate host.

**Most BugBane tools work with the bugbane.json configuration file**: they get input variables, update their values, and add new variables to existing config file.<br>

<details>
<summary>
Example of an input configuration file which is sufficient to run all BugBane tools in sequence
</summary>

```json
{
    "fuzzing": {
        "os_name": "Arch Linux",
        "os_version": "Rolling",

        "product_name": "RE2",
        "product_version": "2022-02-01",
        "module_name": "BugBane RE2 Example",
        "application_name": "re2",

        "is_library": true,
        "is_open_source": true,
        "language": [
            "C++"
        ],
        "parse_format": [
            "RegExp"
        ],
        "tested_source_file": "re2_fuzzer.cc",
        "tested_source_function": "TestOneInput",


        "build_cmd": "./build.sh",
        "build_root": "./build",
        "tested_binary_path": "re2_fuzzer",
        "sanitizers": [
            "ASAN", "UBSAN"
        ],
        "builder_type": "AFL++LLVM",
        "fuzzer_type": "AFL++",

        "run_args": null,
        "run_env": null,
        "timeout": null,

        "fuzz_cores": 16
    }
}
```

</details>

The corpus, coverage, reproduce, and report utilities support an **alternative run mode (the manual run mode)** , the screenshot utility works only in this alternative mode. The manual run mode gives more fine-grained control over settings and allows using the tools listed separately from the other BugBane tools.<br>

## bb-build
Creates multiple builds of a given tested application with use of fuzzer compilers.<br>
The tool is only suited for C/C++ apps, thus, go-fuzz and go-test targets are not supported.<br>

Example usage:
```shell
bb-build -i /src -o /fuzz
```
The /src directory must contain the bugbane.json file.<br>
As a result, build directories appear in the /fuzz path, for example: /fuzz/basic, /fuzz/asan, /fuzz/coverage. Also, build logs appear in the /fuzz folder, the logs contain the commands and the environment variables used to perform builds.

<details>
<summary>Details on how bb-build works</summary>

The inputs to the tool are the following:
1. The source code of a tested app
2. A build script or some build-starting command
3. The bugbane.json configuration file

The bugbane.json should define variables: `builder_type`, `build_cmd`, `build_root`, `sanitizers`.<br>

The `build_cmd` script or command should respect the CC, CXX, LD, CFLAGS, CXXFLAGS, LDFLAGS environment variables and should build the tested application in fuzz testing mode (so it should enable fuzzing entrypoints / harnesses). After one execution of `build_cmd` there should appear one build of the tested app in the `build_root` directory. The `sanitizers` variable should contain list of sanitizers to build the app with. BugBane performs a separate build for each specified sanitizer.<br>

bb-build sequentially performs multiple builds of the tested app (with different sanitizers + with coverage + with special instrumentation like cmplog or laf), and results of each build are then saved from `build_root` to the directory provided as an argument to the `-o` option. This updates some variables in the bugbane.json file (in particular, `sanitizers` is filled with the names of sanitizers for which the build was successful).<br>

Example of a script to specify in `build_cmd`:
```bash
#!/bin/bash
set -x

export CXX="${CXX:-afl-clang-fast++}"

rm -rf build
mkdir -p build
test -e Makefile && make clean

make -j obj/libre2.a
$CXX $CXXFLAGS --std=c++11 -I. re2/fuzzing/re2_fuzzer.cc /AFLplusplus/libAFLDriver.a obj/libre2.a -lpthread -o build/re2_fuzzer
```
When using such a script, compilation flags can be controlled externally using environment variables allowing you to get builds with any sanitizers, coverage instrumentation, debug information, etc.

</details>

### Directories to builds mapping
<details>
<summary>The following table shows where bb-build tool saves the build results</summary>

| Directory name | Description | builder_type |
|-|-|-|
| basic | Build for fuzzing. This must be the most performant build: without sanitizers or coverage | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer |
| gofuzz | Build for fuzzing with dvyukov/go-fuzz (zip archive). Not supported by bb-build, supported by the other BugBane tools | - |
| gotest | Build for fuzzing, compiled with `go test`. Not supported by bb-build, supported by the other BugBane tools | - |
| laf | Build for fuzzing, compiled with the AFL_LLVM_LAF_ALL env variable | AFL++LLVM, AFL++LLVM-LTO |
| cmplog | Build for fuzzing, compiled with the AFL_USE_CMPLOG env variable | AFL++LLVM, AFL++LLVM-LTO |
| asan | Build for fuzzing with Address Sanitizer | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer
| ubsan | Build for fuzzing with Undefined Behavior Sanitizer | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer
| cfisan | Build for fuzzing with Control Flow Integrity Sanitizer | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer
| tsan \* | Build for fuzzing with Thread Sanitizer | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer
| lsan \* | Build for fuzzing with Leak Sanitizer. This sanitizer is included in ASAN, but can also be used separately | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer
| msan \* | Build for fuzzing with Memory Sanitizer | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer
| coverage | Build for coverage collection | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer

\* This wasn't tested.<br>
</details>

### Building without bb-build
It's not always convenient to perform builds using bb-build, for example, when different people do building and fuzzing. Also, bb-build doesn't support automatic builds for Go targets.<br>

<details>

<summary>The following are instructions to ensure compatibility between own builds and the BugBane utilities.</summary>

#### C/C++
All builds are recommended to be performed by fuzzer compilers, including coverage builds.<br>
All builds must be created with debug information containing source lines (`-g` for gcc, `-g` or `-gline-tables-only` for clang).<br>
All builds must be performed with the flag `-fno-omit-frame-pointer` in order for binaries to provide better stack traces when reproducing bugs or when debugging the binaries manually.<br>
If the fuzzer compilers support environment variables for enabling sanitizers (AFL_USE_ASAN, etc.), then using these variables is preferred over specifying compilation flags manually.<br>
The builds should be placed in appropriately named folders. For example, if fuzzing starts from the /fuzz directory, then an ASAN-instrumented build should be saved under the /fuzz/asan folder. If a build is instrumented with multiple sanitizers, then it's sufficient to save this build in either sanitizer directory. For instance, a build with ASAN, UBSAN, and CFISAN can be placed in either asan, ubsan, cfisan, lsan, tsan, or msan directory - this will not reduce the effectiveness of fuzzing or bugs reproducing. Though, it is *recommended* to create copies or symlinks according to the sanitizers (/fuzz/asan, /fuzz/ubsan, ...).<br>
If the build process in CI takes time comparable to the fuzz testing time, then it may be worth to just use a single build that simultaneously includes instrumentation of the fuzzer, coverage, and sanitizers. This negatively affects fuzzing performance and creates additional disk load, but it still may be preferable to doing multiple builds. To use a single build of an app, compiled with both ASAN and coverage flags, place the build in the /fuzz/asan folder and then copy (or symlink) it to the /fuzz/coverage path.<br>

#### Go

##### dvyukov/go-fuzz
Go to the folder of a project to test and execute the following command:
```shell
go-fuzz-build
```
More information is available on [the project page](https://github.com/dvyukov/go-fuzz).

##### go test
The following instructions are for the built-in fuzzer which was introduced with the release of go1.18.<br>
Go to the folder of a project to test and run the following command:
```shell
go test . -fuzz=FuzzMyFunc -o fuzz -c -cover
```
Replace FuzzMyFunc with the name of any fuzz test present in the code base. The function name must start with "Fuzz" (see [the fuzzer documentation](https://go.dev/security/fuzz)).<br>
The result is the `fuzz` executable file with an option to run any of the available fuzzing tests. For example, if the code contains the `FuzzHttp` and `FuzzJson` tests, then you can build the app with the option `-fuzz=FuzzHttp`, and as a result, you will be able to run fuzzing with the either option: `-test.fuzz=FuzzHttp` or `-test.fuzz=FuzzJson`.<br>
The build option `-cover` has no effect yet, because fuzzing and coverage are temporarily incompatible in Go. Using the option isn't mandatory, but allows you to avoid making changes in the future when the Go developers bring back fuzzing and coverage compatibility.<br>

</details>

## bb-corpus
Synchronizes test cases between a fuzzer's working directory and a storage.<br>

Example of importing input test cases before fuzzing:
```shell
bb-corpus suite /fuzz import-from /storage
```
In this case the /fuzz folder is a fuzzer's working directory (containing bugbane.json), the /storage is a storage directory, in which there is the samples folder. The /storage/samples directory contains test case files.

After fuzzing, new test cases should be added to the storage:
```shell
bb-corpus suite /fuzz export-to /storage
```

<details>
<summary><b>Support for the built-in Go fuzzer (go test) is limited</b></summary>

Sample exporting works fine, but importing requires using of one of the following options:
- use `bb-corpus manual` and specify the folder of a specific fuzzing test (for example, out/FuzzXxx) as the output directory
- use `bb-corpus suite`, but pre-define the variable `fuzz_in_dir` in the config file (similarly: out/FuzzXxx)
- copy the samples by other means (rsync, cp)

</details>

<details>
<summary>Details on how bb-corpus works</summary>

The tool supports importing test cases from the storage to the fuzzer working directory and exporting them from the fuzzer working directory back to the storage.<br>
The storage is just a mounted directory, which can in turn be some Samba share, an NFS drive, etc.<br>

Synchronization occurs in two stages:
1. Copying samples (if importing) or moving them (if exporting) from a source directory to a temporary folder without creating duplicates (SHA1 hash sum checks are in place).
2. Minimizing the samples in the temporary folder, saving results to a destination directory using fuzzer tools (such as afl-cmin)

The variable `fuzzer_type` must be defined in the configuration file bugbane.json.<br>
For afl-cmin minimization there must be builds of a tested app on disk. The most preferred build for minimizing samples is the one in the `laf` folder, as it "distinguishes" more execution paths, though, if this build is missing, bb-corpus uses the other builds for minimization.

The names of resulting files contain the SHA1 hash sum of their contents. If the destination directory already contains files with the matching names, no file overwriting occurs.

</details>

## bb-fuzz
Launches fuzzing of an app under test using a specified number of CPU cores, stops fuzzing when a specified stop condition occurs.<br>

Example usage:
```shell
FUZZ_DURATION=1800 bb-fuzz --max-cpus $(nproc) suite /fuzz
```
As a result, multiple fuzzer instances start running in a tmux session.<br>
The bb-fuzz tool will periodically print run statistics of the fuzzer until it detects the occurrence of a stop condition, in this case, until the duration of 1800 seconds (30 minutes) has passed.<br>
Then the tool saves fuzzer screen dumps (text representations) to the /fuzz/screens directory. The dumps are for the bb-report or bb-screenshot tools to create screenshots from in the next stages.<br>
**Warning: after saving the dumps ALL afl-fuzz and tmux processes in the whole operating system are terminated.**<br>

<details>
<summary>Details on how bb-fuzz works</summary>

The tool detects builds of a tested app on disk and distributes them across different processor cores.<br>
The distribution algorithm for C/C++ builds relies on the following rules:
* builds with sanitizers are allocated one core each;
* auxiliary builds (AFL_LLVM_LAF_ALL, AFL_USE_CMPLOG) are assigned to a certain proportion of the available cores;
* the basic build (without sanitizers) occupies the remaining cores;
* builds for source code coverage collection do not participate in fuzz testing (see bb-coverage).

When fuzzing Go applications, there's only one build (in either `gofuzz` or `gotest` folder) which is allocated to all available cores.<br>
For the built-in Go fuzzer (go test) bb-fuzz exits on the first bug discovered. This is caused by the way the fuzzer works. If there are no detected bugs, the work continues as usual until a stop condition occurs.<br>

The bugbane.json configuration file must define the variables `fuzzer_type`, `tested_binary_path`, `fuzz_cores`, `src_root`, `run_args`, `run_env`, and `timeout`. The variable `timeout` is specified in milliseconds.<br>
The builds of the app to test must exist on disk in folders corresponding to the build type, just as the bb-build tool places them.<br>
There may also be dictionary files with the ".dict" extension in the "dictionaries" folder. They are merged into one dictionary, which is provided for the fuzzer to use, subject to the support from the fuzzer.

The values available for the variable `fuzzer_type`: AFL++, libFuzzer, go-fuzz, go-test.<br>
The variable `tested_binary_path` holds the path to the tested app's binary relative to an input directory (where builds will be searched for). Example: imagine, there's a folder named "build" with the build results, executable is named "app" and is saved as build/test/app, the bb-build tool performed several builds each time copying the "build" folder to path /fuzz, that is, now there are paths /fuzz/basic/test/app, /fuzz/coverage/test/app, etc. In this case the `tested_binary_path` should be "test/app".<br>
The variable `src_root` is not used directly, but other BugBane tools running after bb-fuzz fail if the variable is missing.<br>
The `run_args` variable holds a string containing run arguments for the tested app. The variable may include the "@@" sequence, through which the fuzzer may provide input samples for the app.<br>
For the built-in Go fuzzer the variable `run_args` must contain the `-test.fuzz` launch option with a specific fuzz test, for instance, `-test.fuzz=FuzzHttp`.<br>
The `run_env` contains a dictionary of environment variables, required to fuzz the tested app. The env variable LD_PRELOAD is automatically converted to a corresponding fuzzer variable (such as AFL_PRELOAD for AFL++).<br>
Example of the `run_env` variable in the configuration file:
```json
"run_env": {
    "LD_PRELOAD": "/src/mylib.so",
    "ENABLE_FUZZ_TARGETS": "1"
}
```
The following stop conditions are available:
* actual fuzzing duration has reached X seconds (time spent regardless of the number of cores / fuzzer instances);
* no new code execution paths have been detected for the last X seconds among all instances of a fuzzer.

The stop condition is defined using the following environment variables:
* CERT_FUZZ_DURATION=X - X specifies the number of seconds without no new execution paths detected; this variable has the highest priority if other stop condition variables are set;
* CERT_FUZZ_LEVEL=X - X specifies so called "control level", which in turn defines the number of seconds without no new execution paths, available values of X are: 2, 3, 4; this variable has medium priority;
* FUZZ_DURATION=X - X specifies fuzzing duration (number of seconds); this variable has the lowest priority.

The CERT_FUZZ_\* variables are fit for software certification trials, and the FUZZ_\* variables are intended to be used in CI/CD.<br>
If none of the above variables are defined, then FUZZ_DURATION=600 is used implicitly.<br>

The number of processor cores to use in fuzzing is determined by the minimal value of the following:
1. The number of CPU cores available in the OS.
2. The value of the `fuzz_cores` variable of the configuration file. If the variable is not specified, the value of 8 is used.
3. The value of the `--max-cpus` run argument, default is 16.

Thus, the number of processor cores is limited by both the author of the bugbane.json file (presumably, the developer of the tested application), and the end user of BugBane (presumably, an Application Security specialist).

</details>

## bb-coverage
Collects coverage of a tested app using the test cases, generated during fuzz testing.<br>

Example usage:
```shell
bb-coverage suite /fuzz
```
As a result, coverage report files appear under the /fuzz/coverage_report directory, with the /fuzz/coverage_report/index.html being the main page of the report.<br>
**The tool does not work for the built-in Go fuzzer (go test).** This is due to the way the fuzzer works.

<details>
<summary>Details on how bb-coverage works</summary>

For C/C++ apps the tool does the following:
1. Runs an app under test on samples in the sync directory of a fuzzer
2. Generates a coverage report

For Go apps, the tool works differently:
1. Generates a coverage report using the coverage profiles, generated while fuzzing with the launch option `-dumpcover` \*
2. Changes the background color of the report from black to white

\* bb-fuzz uses this option.

The configuration file bugbane.json should define the variables `tested_binary_path`, `run_args`, `run_env`, `coverage_type`, `fuzzer_type`, `fuzz_sync_dir`, and `src_root`.<br>
The `coverage_type` variable gets set by bb-build and matches the builder type used there.<br>
The `src_root` variable holds the path to the source code of the tested app, which existed during the build process; the path does not have to actually exist on the file system during coverage collection: if the directory doesn't exist, then resulting coverage report shows coverage percentages, but not the code itself.

Possible values of the `coverage_type` variable
| coverage_type | Description |
|-|-|
| lcov | For targets built with GCC compilers and the `--coverage` flag |
| lcov-llvm | For targets built with LLVM compilers and the `--coverage` flag |
| go-tool-cover | For Go targets |

</details>

## bb-reproduce
Reproduces fuzzer-discovered crashes and hangs and summarizes the results of a fuzzing campaign.<br>

Example usage:
```shell
bb-reproduce suite /fuzz
```

This generates the file /fuzz/bb_results.json, containing the fuzzer statistics and information about reproducible bugs. Test cases for the bugs reproduced are saved under the /fuzz/bug_samples directory.<br>

<details>
<summary>Details on how bb-reproduce works</summary>

The bb-reproduce tool does the following:
1. Collects the overall statistics of fuzzers' operation
2. Minimizes crashes and hangs by reproducing them
3. Records information about each unique reproducible bug
4. Generates a JSON file with the stats and the bugs data
5. Saves test cases resulting in reproducible crashes and hangs to disk

The data saved for each reproducible bug includes the issue/bug title, the location of the bug in the source code, the run command with a particular test sample, the app output (stdout+stderr), the environment variables, etc.<br>
Targets instrumented with [SharpFuzz](https://github.com/Metalnem/sharpfuzz) are also supported by the tool.

The bugbane.json configuration file must define the variables `src_root`, `fuzz_sync_dir`, `fuzzer_type`, `reproduce_specs`, `run_args`, and `run_env`. The variables `fuzz_sync_dir` and `reproduce_specs` are usually set by the bb-fuzz tool.<br>
The `fuzz_sync_dir` contains the path to the fuzzer synchronization directory; bb-fuzz uses the "out" directory.<br>
The `src_root` is the root directory of the tested app's source code as it was at the time of build; the path does not have to exist on the file system as the variable is only used for better precision when locating the crashing/hanging line in the source code.<br>
The `reproduce_specs` is a JSON dictionary, specifying the fuzzer type and mapping the builds of the tested app to the folders, on which to reproduce bugs:
```json
"fuzz_sync_dir": "/fuzz/out",
"reproduce_specs": {
    "AFL++": {
        "/fuzz/basic/app": [
            "test1"
        ],
        "/fuzz/ubsan/app": [
            "test2",
            "test3"
        ]
    }
}
```
In the above example the `basic` build (/fuzz/basic/app) will be run with the samples matching the pattern `/fuzz/out/test1/{crashes,hangs}/id*`, and for the `ubsan` build (/fuzz/ubsan/app) the pattern will be `/fuzz/out/test{2,3}/{crashes,hangs}/id*`.<br>

The output of the tested app is analyzed on each reproduce try, for example, the tool searches for sanitizer messages. Each bug sample is tried until a successful bug detection, but not more than N times. The number N is defined by the `--num-reruns` argument of bb-reproduce (the default value is 3). When trying a crashing sample, if the app does not produce the stack trace, then the app is ran under the gdb debugger. Hangs are always reproduced under gdb.<br>

</details>

### Viewing the bugs information
Information about the bugs discovered may be displayed in the terminal with the jq utility (installed separately).<br>
This allows you to view and report bugs manually, for example, if you don't use Defect Dojo or the bb-send tool.<br>

To get a simple text representation for viewing in the terminal use the command:
```shell
jq '.issue_cards[] | "-" * 79, .title, .reproduce_cmd, .output, "Saved sample name", .sample, ""' -rM bb_results.json
```

To get an issue text ready for GitHub use the following:
````shell
jq '.issue_cards[] | "## \(.title)", "Originally reproduced by executing: \n```shell\n\(.reproduce_cmd)\n```", "Output:\n```\n\(.output)```", "Saved sample name: \(.sample)", ""' -rM bb_results.json
````

To get an issue text ready for Jira use this:
````shell
jq '.issue_cards[] | "h1. \(.title)", "Originally reproduced by executing: \n{noformat}\n\(.reproduce_cmd)\n{noformat}", "Output:\n{noformat}\n\(.output){noformat}", "Saved sample name: \(.sample)", ""' -rM bb_results.json
````

It's recommended to create an issue for each separate bug, as the bugs have already been deduplicated by bb-reproduce and are already unique with high probability.<br>
If it's preferred to create a single issue for all discovered bugs, then it's sufficient to attach to it an archive with the `bug_samples` directory.<br>

## bb-send
Puts reproducible bugs in the Defect Dojo vulnerability management system.<br>
The input data is taken from the bb_results.json file, created by the bb-reproduce tool.<br>
The bugbane.json file is not used.<br>

Example usage:
```shell
export BB_DEFECT_DOJO_SECRET="DD_TOKEN"
bb-send --host https://dojo.local \
    --user-name ci_fuzz_user --user-id 2 \
    --engagement 1 --test-type 141 \
    --results-file bb_results.json
```
As a result, a new test appears with the test type 141 in the engagement having the id 1 on the Defect Dojo server hosted at `https://dojo.local`. Each bug is created separately from the other ones in this new test.

<details>
<summary>Details on some of the bb-send run options</summary>

Hereinafter `https://dojo.local` is used as the address of the Defect Dojo server.<br>
`--user-id`: id of the user specified in the `--user-name` option; may be taken from the Defect Dojo's url, while desired user is selected on the page `https://dojo.local/user`.<br>
`--engagement`: engagement id; may also be taken from the engagement url (select one on the page `https://dojo.local/engagement`).<br>
`--test-type`: test type id; also comes from the url (select required test type on the page `https://dojo.local/test_type`).<br>
`--token`: API key; copied from the page `https://dojo.local/api/key-v2` (you need to be authorized with the name specified in the `--user-name` option, you need the API key from the part, starting with "Your current API key is ....").<br>
You are advised to use the env variables `BB_DEFECT_DOJO_LOGIN` and `BB_DEFECT_DOJO_SECRET` instead of the args `--user-name` and `--token`.<br>

If the authenticity of the Defect Dojo server certificate cannot be verified, the `--no-ssl` option should be added.

</details>

## bb-report
Generates a Markdown fuzz test report based on a specified Jinja2 template.<br>
The default template contains textual description of the fuzzing process in Russian and includes the commands used to start fuzzers, the fuzzer screenshots, some of the stats, etc.<br>

The tool creates screenshots of the following:
1. the fuzzer - made from the tmux dumps, saved by the bb-fuzz tool
2. the main page of the coverage report, which was generated by the bb-coverage tool

The screenshots are saved to the "screenshots" folder and inserted into the report as links.<br>
The configuration file bugbane.json should define the variables `fuzzer_type`, `coverage_type`, and `fuzz_sync_dir`.<br>

Example usage:
```shell
bb-report --name myapp_fuzz suite /fuzz
```

Example usage with Selenium:
```shell
bb-report --html-screener selenium --name myapp_fuzz suite /fuzz
```

As a result, the screenshots folder appears in the /fuzz directory with the images and the report file `myapp_fuzz.md`.<br>

In order to create a report in the DOCX format you can use the pandoc tool (installed separately):
```shell
pandoc -f markdown -t docx myapp_fuzz.md -o myapp_fuzz.docx
```

## bb-screenshot
Creates images from a user-provided HTML files, simple text files, or files containing ANSI sequences. The images are made in the same way, as in the bb-report tool, but the user may specify input and output paths.<br>

Usage examples:
```shell
bb-screenshot -S pango -i tmux_dump.txt -o tmux_screenshot.png
bb-screenshot -S weasyprint -i index.html -o coverage.png
bb-screenshot -S selenium -i index.html -o coverage2.png
```

# Improvements

Future plans for BugBane:
* add support for more fuzzers
* add more tools
* add more report templates and support different reporting formats

# For developers
Install the project in editable mode using a virtual environment:
```
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

Run the pytest suite:
```
pytest
```

# Acknowledgements
Thank you to everyone involved in the project!

Special thanks:
- [Ilya Urazbakhtin](https://github.com/donyshow): ideas, consultations, mentoring.
