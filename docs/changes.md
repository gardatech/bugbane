# BugBane changelog
List of significant changes in BugBane.

## Version 0.5.1
- build tool:
    - **(breaking change)** bb-build now saves updated configuration file to output directory, initial file is now left intact.<br>
        Now there's no need to manually copy the file after using bb-build
    - improved output directory cleanup algorithm.<br>
        Now bb-build only removes subdirectories (e.g. basic, asan, coverage) instead of removing the whole `-o` directory,<br>
        so it is now safe to have files in output directory before using bb-build
- fuzz tool:
    - dictionary merging algorithm now removes token names, thus removing duplicate tokens with different names
- screenshot tool:
    - changed default dpi used for pango-view from 180 to 128 to match dpi used by report tool

## Version 0.5.0
- added support for native Go fuzzer (introduced in go1.18).<br>
  The support is limited due to current limitations of the fuzzer:
    - go fuzzer will bail immediately at the first found bug, hence bb-fuzz will exit as well
    - go fuzzer doesn't allow collecting coverage during fuzzing, hence bb-coverage will not work at all
    - go fuzzer doesn't have a concept of input samples directory, hence importing samples with bb-corpus will require additional fiddling
- fixed libFuzzer "time without finds" stop condition detection

## Version 0.4.4
- reproduce tool:
    - now normalizes crash/hang location in issue title: "Crash in /src/a/b/../../c.cpp:20" -> "Crash in /src/c.cpp:20"
    - now uses absolute paths in stack traces produced by gdb
    - now detects unhandled exceptions in stacktraces produced by C#
- better README

## Version 0.4.3
- **(breaking change)** bb-fuzz syntax updated to match other tools.<br>
    Users will need to remove dashes from `suite` option: change `bb-fuzz --suite $DIR` to `bb-fuzz suite $DIR`
- all tools that run tested application now support `run_env` variable (bb-fuzz replaces LD_PRELOAD with similar fuzzer variable, e.g. AFL_PRELOAD for AFL++)

## Version 0.4.2
- fixed timeout option
- added reproduce tool option `--hang-reproduce-limit=R` to test at most R hangs per fuzzer instance (R=3 by default)
- added fuzz tool option `--start-interval` to specify delay between starting fuzzer instances
- better bug title when detecting memory leaks reported by ASAN/LSAN

## Version 0.4.1
- added timeout option
- fixed parsing of AFL++ fuzz stats in newer format which was introduced in AFL++ 4.00
- fixed reproduce specs being limited to just one fuzzer subdirectory per build for AFL++

## Version 0.4.0
- added support for fuzzing dictionaries

## Version 0.3.0
- made public under Apache-2.0 license
- new README

## Version 0.2.0
- added dvyukov/go-fuzz support to all BugBane tools except for the build tool
- screenshot tool:
    - added Selenium support for HTML

## Version 0.1.0
- build tool:
    - makes target builds suitable for fuzzing
    - supports different build types (sanitizers, coverage, etc)
    - AFL++ builder (afl-gcc, afl-gcc-fast, afl-clang-fast, afl-clang-lto)
    - libFuzzer builder (clang)
- corpus tool:
    - moves fuzzer-generated samples between fuzzer sync dir and storage (both ways)
    - sha1-based deduplication
    - tool-based minimization (afl-cmin)
- fuzz tool:
    - runs fuzzers with tested application builds allocated to different CPU cores
    - supports time-based stop conditions
    - AFL++ support
    - libFuzzer support
- coverage tool:
    - runs coverage build of tested application on fuzzer-generated samples
    - lcov coverage collectors and report generators for targets built with `--coverage` flag using gcc (lcov) or clang (lcov-llvm)
    - lcov HTML report parser
    - llvm-cov summary.txt report parser (unused yet)
- reproduce tool:
    - runs tested application on fuzzer-generated crashes and hangs
    - extracts bugs' descriptions (generic crashes, sanitizer messages, gdb stacktraces)
- send tool
    - sends reproduce results to vulnerability management system
    - Defect Dojo support
- report tool:
    - generates fuzzing report with use of Jinja2 templates
    - Markdown generator
- screenshot tool:
    - converts files to images
    - uses ansifilter and pango-view tools for tmux dumps of fuzzer screens
    - uses WeasyPrint python library for HTML coverage reports


Initial commit: 2021-10-21
