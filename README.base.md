<!---------------------------->
<!-- multilingual suffix: en, ru -->
<!-- no suffix: en -->
<!---------------------------->

<!-- NOTE: this is a template file to be used with https://github.com/ryul1206/multilingual-markdown -->

<!-- [common] -->
# BugBane

<!-- [ru] -->
🌍 [**English**](README.md) | Русский

<!-- [en] -->
🌍 English | [**Русский**](README.ru.md)

<!-- [ru] -->
Набор утилит для автоматизации фаззинг-тестирования.<br>

<!-- [en] -->
Fuzz testing automation toolkit.<br>

<!-- [ru] -->
# Возможности

<!-- [en] -->
# Features

<!-- [ru] -->
Цели BugBane:
1. Упрощение пайплайна CI-фаззинга путём обобщения типичных этапов тестирования и стандартизации конечных артефактов.
2. Выполнение фаззинга в эффективной конфигурации с учётом лучших практик.
3. Генерация отчётных материалов в соответствии с реально выполняемыми действиями.

<!-- [en] -->
BugBane goals:
1. CI fuzzing pipeline simplification by generalizing typical testing steps and standardizing the resulting artifacts.
2. Performing fuzzing in an efficient configuration based on best practices.
3. Reports generation in accordance with the actual actions performed.

<!-- [ru] -->
Возможности BugBane:
1. Сборка приложений для фаззинг-тестирования, в том числе с санитайзерами и покрытием: AFL++, libFuzzer.
2. Фаззинг сборок с использованием [AFL++](https://github.com/AFLplusplus/AFLplusplus), [libFuzzer](https://www.llvm.org/docs/LibFuzzer.html), [dvyukov/go-fuzz](https://github.com/dvyukov/go-fuzz), [go test](https://go.dev/security/fuzz) на заданном количестве ядер до заданного условия остановки.
3. Синхронизация тестовых примеров между рабочей директорией фаззера и хранилищем. Включает отсеивание дубликатов и минимизацию на основе инструментов фаззера.
4. Сбор покрытия тестируемого приложения на семплах, полученных в процессе фаззинг-тестирования, а также генерация HTML-отчётов о покрытии.
5. Воспроизведение падений и зависаний, обнаруженных фаззером. Определение места возникновения ошибки и отсеивание дубликатов.
6. Отправка сведений о воспроизводимых багах в систему управления уязвимостями: [Defect Dojo](https://github.com/DefectDojo/django-DefectDojo).
7. Получение скриншотов работы фаззера и главной страницы отчёта о покрытии исходного кода.
8. Генерация отчётов на основе шаблонов Jinja2.

<!-- [en] -->
BugBane features:
1. Building applications for fuzz testing with sanitizers and coverage support: AFL++, libFuzzer.
2. Fuzzing built targets with [AFL++](https://github.com/AFLplusplus/AFLplusplus), [libFuzzer](https://www.llvm.org/docs/LibFuzzer.html), [dvyukov/go-fuzz](https://github.com/dvyukov/go-fuzz), [go test](https://go.dev/security/fuzz) using a given number of CPU cores until meeting a given stop condition.
3. Synchronizing test cases between fuzzer and storage directories, including deduplication and minimization with use of fuzzer tools.
4. Coverage collection of tested app's source code using fuzzer-generated samples, coverage reports creation.
5. Reproducing of fuzzer-discovered crashes and hangs. Determining location of bugs in the source code.
6. Submitting reproducible bugs to vulnerability management system: [Defect Dojo](https://github.com/DefectDojo/django-DefectDojo).
7. Creating screenshots for both fuzzers and coverage reports.
8. Report generation with use of Jinja2 templates.

<!-- [ru] -->
Утилиты BugBane связаны между собой, но использовать их вместе совсем не обязательно.

<!-- [en] -->
The BugBane utilities are best used together, though they're also usable on their own.

<!-- [ru] -->
# Установка

<!-- [en] -->
# Install

<!-- [ru] -->
## Зависимости
UNIX-подобная ОС<br>
Python >= 3.6<br><br>
Зависимости, используемые утилитами BugBane:<br>
**bb-build**: компиляторы используемого фаззера в PATH (afl-g++-fast, clang, ...).<br>
**bb-corpus**: утилита минимизации в соответствии с используемым фаззером в PATH (afl-cmin, ...).<br>
**bb-fuzz**: используемый фаззер в PATH (afl-fuzz, go-fuzz, ...).<br>
**bb-coverage**: используемые средства сбора покрытия в PATH (lcov, genhtml, go, ...).<br>
**bb-reproduce**: утилита `timeout`, отладчик `gdb`.<br>
**bb-send**: -.<br>
**bb-screenshot**, **bb-report**: приложения `ansifilter` и `pango-view` в PATH, приложение `geckodriver` в PATH и браузер Firefox (необязательно, только для Selenium), шрифты `mono` (могут отсутствовать в базовых образах Docker).<br>
Примечания:
- скриншоты покрытия с Selenium выглядят лучше, чем с WeasyPrint, но требуют установку браузера Firefox и geckodriver;
- скриншоты покрытия для Go требуют использовать Selenium, потому что Go встраивает в отчёты JavaScript;
- для просмотра отчётов непосредственно в образе Docker с помощью утилит типа less может потребоваться установка локали с поддержкой UTF-8 и указание переменной LANG.

<!-- [en] -->
## Requirements
UNIX-like OS<br>
Python >= 3.6<br><br>
Dependencies required by the tools:<br>
**bb-build**: fuzzer compilers in PATH (afl-g++-fast, clang, ...).<br>
**bb-corpus**: fuzzer minimization tools in PATH (afl-cmin, ...).<br>
**bb-fuzz**: fuzzer binary in PATH (afl-fuzz, go-fuzz, ...).<br>
**bb-coverage**: coverage tools to be used in PATH (lcov, genhtml, go, ...).<br>
**bb-reproduce**: the `timeout` utility, the `gdb` debugger.<br>
**bb-send**: -.<br>
**bb-screenshot**, **bb-report**: the applications `ansifilter` and `pango-view` in PATH, `geckodriver` in PATH and the Firefox web browser (optional, only for Selenium functionality), any `mono` fonts (may be missing in Docker images).<br>
Notes:
- screenshots of coverage reports look better when created with Selenium rather than with WeasyPrint, though Selenium requires Firefox and geckodriver;
- Go coverage reports require Selenium to create screenshots, because Go coverage reports heavily rely on JavaScript;
- in order to view reports in docker container with utils like `less` it may be required to generate a locale with UTF-8 support and to set the LANG env variable.

<!-- [ru] -->
## Установка и удаление пакета
Установить пакет можно локально с помощью pip:
```
git clone https://github.com/gardatech/bugbane
cd bugbane
pip install .[all]
```
Проверить выполнение тестов:
```
pytest
```

<!-- [en] -->
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

<!-- [ru] -->
<details>
<summary>Дополнительные инструкции</summary>

Вместо "all" доступны другие группы, позволяющие установить только необходимые Python-зависимости:
| Группа pip install | Фаззинг\* | Заведение багов в Defect Dojo | Отчёты и скриншоты | Тестирование BugBane | Разработка BugBane |
<!-- [en] -->
<details>
<summary>Additional setup instructions</summary>

There are install groups available other than "all", which allow smaller installations with only required Python dependencies:
| pip install group | Fuzzing\* | Submitting bugs to Defect Dojo | Reports and screenshots | BugBane testing | BugBane development |
<!-- [common] -->
|-|-|-|-|-|-|
| - | + | - | - | - | - |
| dd | + | + | - | - | - |
| reporting | + | - | + | - | - |
| test | + | - | - | + | - |
| all | + | + | + | + | - |
| dev | + | + | + | + | + |

<!-- [ru] -->
\* Выполнение сборок, фаззинг, работа с семплами, сбор покрытия и воспроизведение багов.

<!-- [en] -->
\* Performing builds, fuzz testing, corpus syncing, coverage collection, and bug reproducing.

<!-- [ru] -->
Таким образом, можно разделить тестирование и работу с его результатами на разные хосты `worker` и `reporter`:
<!-- [en] -->
Thus, it's possible to separate fuzz testing and working with its results to different hosts, for instance, `worker` and `reporter`:
<!-- [common] -->
```shell
pip install .                  # worker
pip install .[dd,reporting]    # reporter
```
<!-- [ru] -->
Результат: на хосте `worker` не требуются зависимости для генерации отчётов, на хосте `reporter` не требуется окружение для запуска тестируемых приложений и фаззеров.

Для удаления использовать следующую команду:
<!-- [en] -->
As a result, the `worker` host doesn't need report generation dependencies, and the `reporter` host doesn't need an environment to run tested applications or fuzzers.

To uninstall BugBane use the following command:
<!-- [common] -->
```
pip uninstall bugbane
```

</details>

<!-- [ru] -->
# Запуск
Рекомендуется использовать BugBane в среде Docker.<br>
Подразумевается последовательный запуск инструментов в определённом порядке, например:
<!-- [en] -->
# How to use
It is recommended to use BugBane in a Docker environment.<br>
Sequential use of the tools is implied, for example:
<!-- [common] -->
1. bb-build
2. bb-corpus (import)
3. bb-fuzz
4. bb-coverage
5. bb-reproduce
6. bb-corpus (export)
7. bb-send
8. bb-report

<!-- [ru] -->
При этом этап №1 является опциональным, покольку сборки могут быть выполнены другими способами, а этапы №7 и №8 могут выполняться в отдельном образе Docker или на отдельной машине.

**Большинство инструментов BugBane работают с конфигурационным файлом bugbane.json**: получают входные переменные, обновляют их значения и добавляют новые переменные в существующий файл конфигурации.<br>

<!-- [en] -->
However, step #1 is optional, as builds can be done by other means, and steps #7 and #8 can be performed in a separate Docker image or on a separate host.

**Most BugBane tools work with the bugbane.json configuration file**: they get input variables, update their values, and add new variables to existing config file.<br>

<!-- [common] -->
<details>
<summary>
<!-- [ru] -->
Пример исходного файла конфигурации, достаточного для последовательного запуска всех инструментов BugBane
<!-- [en] -->
Example of an input configuration file which is sufficient to run all BugBane tools in sequence
<!-- [common] -->
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

<!-- [ru] -->
Утилиты corpus, coverage, reproduce и report поддерживают **альтернативный режим запуска (manual run mode)**, утилита screenshot работает только в этом режиме. Режим запуска manual предназначен для более тонкой настройки параметров или для использования отдельно от других инструментов BugBane.<br>

<!-- [en] -->
The corpus, coverage, reproduce, and report utilities support an **alternative run mode (the manual run mode)** , the screenshot utility works only in this alternative mode. The manual run mode gives more fine-grained control over settings and allows using the tools listed separately from the other BugBane tools.<br>

<!-- [common] -->
## bb-build
<!-- [ru] -->
Создаёт сборки тестируемого приложения с использованием компиляторов фаззера.<br>
Инструмент предназначен только для C/C++, цели go-fuzz и go-test не поддерживаются.<br>

Пример запуска:
<!-- [en] -->
Creates multiple builds of a given tested application with use of fuzzer compilers.<br>
The tool is only suited for C/C++ apps, thus, go-fuzz and go-test targets are not supported.<br>

Example usage:
<!-- [common] -->
```shell
bb-build -i /src -o /fuzz
```
<!-- [ru] -->
При этом директория /src должна содержать файл bugbane.json.<br>
В результате в пути /fuzz появляются папки с полученными сборками, например: /fuzz/basic, /fuzz/asan, /fuzz/coverage. Также в папке /fuzz сохраняется журнал выполнения всех сборок с указанием команд запуска и использованных переменных окружения.

<!-- [en] -->
The /src directory must contain the bugbane.json file.<br>
As a result, build directories appear in the /fuzz path, for example: /fuzz/basic, /fuzz/asan, /fuzz/coverage. Also, build logs appear in the /fuzz folder, the logs contain the commands and the environment variables used to perform builds.

<!-- [common] -->
<details>
<!-- [ru] -->
<summary>Подробности о работе bb-build</summary>

На вход инструменту подаются:
1. Исходный код тестируемого приложения
2. Команда или скрипт сборки
3. Файл с переменными bugbane.json

В файле bugbane.json должны быть заданы переменные: `builder_type`, `build_cmd`, `build_root`, `sanitizers`.<br>

Команда, указанная в переменной `build_cmd`, должна учитывать значения переменных окружения CC, CXX, LD, CFLAGS, CXXFLAGS, LDFLAGS и при запуске выполнять сборку тестируемого компонента в режиме фаззинг-тестирования. После выполнения одного запуска команды `build_cmd` в папке `build_root` должна оказаться сборка тестируемого приложения. Переменная `sanitizers` должна содержать список санитайзеров, с которыми требуется выполнить сборки. Для каждого санитайзера BugBane выполняет отдельную сборку.<br>

Приложение последовательно выполняет несколько сборок (с различными санитайзерами + для сбора покрытия + дополнительные сборки для фаззинга) и после каждой сборки сохраняет результаты сборки из папки `build_root` в папку, указанную аргументом запуска `-o`. При этом обновляются некоторые переменные в файле bugbane.json (в частности, `sanitizers` - заполняется названиями санитайзеров, для которых удалось выполнить сборку).<br>

Пример скрипта, путь к которому может быть указан в команде сборки `build_cmd`:
<!-- [en] -->
<summary>Details on how bb-build works</summary>

The inputs to the tool are the following:
1. The source code of a tested app
2. A build script or some build-starting command
3. The bugbane.json configuration file

The bugbane.json should define variables: `builder_type`, `build_cmd`, `build_root`, `sanitizers`.<br>

The `build_cmd` script or command should respect the CC, CXX, LD, CFLAGS, CXXFLAGS, LDFLAGS environment variables and should build the tested application in fuzz testing mode (so it should enable fuzzing entrypoints / harnesses). After one execution of `build_cmd` there should appear one build of the tested app in the `build_root` directory. The `sanitizers` variable should contain list of sanitizers to build the app with. BugBane performs a separate build for each specified sanitizer.<br>

bb-build sequentially performs multiple builds of the tested app (with different sanitizers + with coverage + with special instrumentation like cmplog or laf), and results of each build are then saved from `build_root` to the directory provided as an argument to the `-o` option. This updates some variables in the bugbane.json file (in particular, `sanitizers` is filled with the names of sanitizers for which the build was successful).<br>

Example of a script to specify in `build_cmd`:
<!-- [common] -->
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
<!-- [ru] -->
При использовании подобного скрипта флагами компиляции можно управлять извне с помощью переменных окружения и получать сборки с любыми санитайзерами, с инструментацией для сбора покрытия, с отладочной информацией и т.д.

<!-- [en] -->
When using such a script, compilation flags can be controlled externally using environment variables allowing you to get builds with any sanitizers, coverage instrumentation, debug information, etc.

<!-- [common] -->
</details>

<!-- [ru] -->
### Соответствие сборок и папок
<!-- [en] -->
### Directories to builds mapping
<!-- [common] -->
<details>
<!-- [ru] -->
<summary>В таблице показано, в какие папки инструмент bb-build сохраняет результаты сборки</summary>

| Имя папки | Описание | builder_type |
|-|-|-|
| basic | Сборка для фаззинга. Это должна быть наиболее производительная сборка: без санитайзеров, без покрытия | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer |
| gofuzz | Сборка для фаззинга с использованием dvyukov/go-fuzz (zip-архив). Не поддерживается bb-build, поддерживается остальными утилитами | - |
| gotest | Сборка для фаззинга, скомпилированная с помощью `go test`. Не поддерживается bb-build, поддерживается остальными утилитами | - |
| laf | Сборка для фаззинга, скомпилированная с переменной окружения AFL_LLVM_LAF_ALL | AFL++LLVM, AFL++LLVM-LTO |
| cmplog | Сборка для фаззинга, скомпилированная с переменной окружения AFL_USE_CMPLOG | AFL++LLVM, AFL++LLVM-LTO |
| asan | Сборка для фаззинга с адресным санитайзером (Address Sanitizer) | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer
| ubsan | Сборка для фаззинга с санитайзером неопределённого поведения (Undefined Behavior Sanitizer) | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer
| cfisan | Сборка для фаззинга с санитайзером целостности потока выполнения (Control Flow Integrity Sanitizer) | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer
| tsan \* | Сборка для фаззинга с санитайзером потоков (Thread Sanitizer) | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer
| lsan \* | Сборка для фаззинга с санитайзером утечек памяти (Leak Sanitizer). Этот функционал поддерживается адресным санитайзером, но также может использоваться отдельно | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer
| msan \* | Сборка для фаззинга с санитайзером памяти (Memory Sanitizer) | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer
| coverage | Сборка для получения информации о покрытии | AFL++GCC, AFL++GCC-PLUGIN, AFL++LLVM, AFL++LLVM-LTO, libFuzzer

\* Работоспособность не тестировалась.<br>
<!-- [en] -->
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
<!-- [common] -->
</details>

<!-- [ru] -->
### Выполнение сборок без инструмента bb-build
Не всегда удобно выполнять сборки с помощью bb-build, например, если сборками и фаззингом занимаются разные люди. Также bb-build не поддерживает автоматические сборки для целей на языке Go.<br>

<!-- [en] -->
### Building without bb-build
It's not always convenient to perform builds using bb-build, for example, when different people do building and fuzzing. Also, bb-build doesn't support automatic builds for Go targets.<br>

<!-- [common] -->
<details>

<!-- [ru] -->
<summary>Далее следуют инструкции, позволяющие обеспечить совместимость собственных сборок и утилит BugBane.</summary>
<!-- [en] -->
<summary>The following are instructions to ensure compatibility between own builds and the BugBane utilities.</summary>
<!-- [common] -->

#### C/C++
<!-- [ru] -->
Все сборки рекомендуется выполнять компиляторами фаззера, в том числе сборку для получения информации о покрытии.<br>
Все сборки должны выполняться с отладочной информацией, содержащей сведения о строках исходного кода (`-g` для gcc, `-g` или `-gline-tables-only` - для clang).<br>
Все сборки должны выполняться с флагом `-fno-omit-frame-pointer` для получения более точных стеков вызовов в случае обнаружения багов или при ручной отладке.<br>
Если компиляторы фаззера поддерживают переменные окружения для включения санитайзеров (AFL_USE_ASAN и т.д.), то использование этих переменных предпочтительнее ручного указания флагов компиляции.<br>
Сборки следует размещать в папках под соответствующими названиями. Например, если фаззинг запускается из директории /fuzz, то сборка с ASAN должна быть сохранена в папке /fuzz/asan. Сборку, в которой одновременно присутствуют несколько санитайзеров, достаточно разместить в одном экземпляре в любой одной папке для сборки с санитайзером. Например, сборку с ASAN+UBSAN+CFISAN можно разместить в любой из папок: asan, ubsan, cfisan, lsan, tsan или msan - это не снизит эффективность фаззинга и воспроизведения падений. При этом *рекомендуется* создать несколько копий или символьных ссылок в соответствии с санитайзерами (/fuzz/asan, /fuzz/ubsan, ...).<br>
Если процесс сборки в CI занимает время, сопоставимое с временем фаззинг-тестирования, то можно обойтись единственной сборкой, одновременно включающей инструментацию фаззера, покрытия и санитайзеров. Это негативно скажется на скорости фаззинга, а также создаст дополнительную нагрузку на диск в процессе тестирования, но может быть предпочтительнее выполнения нескольких сборок. Чтобы использовать единственную сборку приложения, скомпилированную одновременно с ASAN и с покрытием, её можно разместить в папке /fuzz/asan, а затем скопировать её (или создать символьную ссылку) в путь /fuzz/coverage.<br>

<!-- [en] -->
All builds are recommended to be performed by fuzzer compilers, including coverage builds.<br>
All builds must be created with debug information containing source lines (`-g` for gcc, `-g` or `-gline-tables-only` for clang).<br>
All builds must be performed with the flag `-fno-omit-frame-pointer` in order for binaries to provide better stack traces when reproducing bugs or when debugging the binaries manually.<br>
If the fuzzer compilers support environment variables for enabling sanitizers (AFL_USE_ASAN, etc.), then using these variables is preferred over specifying compilation flags manually.<br>
The builds should be placed in appropriately named folders. For example, if fuzzing starts from the /fuzz directory, then an ASAN-instrumented build should be saved under the /fuzz/asan folder. If a build is instrumented with multiple sanitizers, then it's sufficient to save this build in either sanitizer directory. For instance, a build with ASAN, UBSAN, and CFISAN can be placed in either asan, ubsan, cfisan, lsan, tsan, or msan directory - this will not reduce the effectiveness of fuzzing or bugs reproducing. Though, it is *recommended* to create copies or symlinks according to the sanitizers (/fuzz/asan, /fuzz/ubsan, ...).<br>
If the build process in CI takes time comparable to the fuzz testing time, then it may be worth to just use a single build that simultaneously includes instrumentation of the fuzzer, coverage, and sanitizers. This negatively affects fuzzing performance and creates additional disk load, but it still may be preferable to doing multiple builds. To use a single build of an app, compiled with both ASAN and coverage flags, place the build in the /fuzz/asan folder and then copy (or symlink) it to the /fuzz/coverage path.<br>

<!-- [common] -->
#### Go

##### dvyukov/go-fuzz
<!-- [ru] -->
Перейти в папку тестируемого проекта и выполнить:
<!-- [en] -->
Go to the folder of a project to test and execute the following command:
<!-- [common] -->
```shell
go-fuzz-build
```
<!-- [ru] -->
Дополнительная информация доступна на [странице проекта](https://github.com/dvyukov/go-fuzz).

<!-- [en] -->
More information is available on [the project page](https://github.com/dvyukov/go-fuzz).

<!-- [common] -->
##### go test
<!-- [ru] -->
Следующие инструкции относятся ко встроенному фаззеру, появившемуся с выходом go1.18.<br>
Перейти в папку проекта и выполнить:
<!-- [en] -->
The following instructions are for the built-in fuzzer which was introduced with the release of go1.18.<br>
Go to the folder of a project to test and run the following command:
<!-- [common] -->
```shell
go test . -fuzz=FuzzMyFunc -o fuzz -c -cover
```
<!-- [ru] -->
Вместо FuzzMyFunc следует подставить название любого фаззинг-теста, присутствующего в кодовой базе. Название функции обязано начинаться с "Fuzz" (см. [документацию фаззера](https://go.dev/security/fuzz)).<br>
В результате получится исполняемый файл `fuzz` с возможностью запуска любого из доступных фаззинг-тестов. Например, если в коде есть тесты FuzzHttp и FuzzJson, то можно выполнить сборку с опцией `-fuzz=FuzzHttp`, а в результате можно будет запускать фаззинг как с опцией `-test.fuzz=FuzzHttp`, так и с `-test.fuzz=FuzzJson`.<br>
Опция сборки `-cover` пока не даёт никакого эффекта, поскольку фаззинг и покрытие в Go временно несовместимы. Использование опции необязательно, но позволит не вносить изменения в будущем, когда разработчики Go вернут совместимость фаззинга и покрытия.<br>

<!-- [en] -->
Replace FuzzMyFunc with the name of any fuzz test present in the code base. The function name must start with "Fuzz" (see [the fuzzer documentation](https://go.dev/security/fuzz)).<br>
The result is the `fuzz` executable file with an option to run any of the available fuzzing tests. For example, if the code contains the `FuzzHttp` and `FuzzJson` tests, then you can build the app with the option `-fuzz=FuzzHttp`, and as a result, you will be able to run fuzzing with the either option: `-test.fuzz=FuzzHttp` or `-test.fuzz=FuzzJson`.<br>
The build option `-cover` has no effect yet, because fuzzing and coverage are temporarily incompatible in Go. Using the option isn't mandatory, but allows you to avoid making changes in the future when the Go developers bring back fuzzing and coverage compatibility.<br>

<!-- [common] -->
</details>

## bb-corpus
<!-- [ru] -->
Синхронизирует тестовые примеры в рабочей директории фаззера с хранилищем.<br>

Пример импорта входных тестовых примеров перед фаззинг-тестированием:
<!-- [en] -->
Synchronizes test cases between a fuzzer's working directory and a storage.<br>

Example of importing input test cases before fuzzing:
<!-- [common] -->
```shell
bb-corpus suite /fuzz import-from /storage
```
<!-- [ru] -->
Папка /fuzz в данном случае является рабочей директорией фаззера (содержит bugbane.json), папка /storage - директория хранилища, в которой присутствует папка samples. Папка /storage/samples содержит файлы тестовых примеров.

После фаззинг-тестирования следует добавить новые тестовые примеры в хранилище:
<!-- [en] -->
In this case the /fuzz folder is a fuzzer's working directory (containing bugbane.json), the /storage is a storage directory, in which there is the samples folder. The /storage/samples directory contains test case files.

After fuzzing, new test cases should be added to the storage:
<!-- [common] -->
```shell
bb-corpus suite /fuzz export-to /storage
```

<details>
<!-- [ru] -->
<summary><b>Поддержка встроенного фаззера Go (go test) ограничена</b></summary>

<!-- [en] -->
<summary><b>Support for the built-in Go fuzzer (go test) is limited</b></summary>

<!-- [ru] -->
Экспорт в хранилище функционирует нормально, а для импорта придётся использовать один из следующих вариантов:
- использовать `bb-corpus manual` и указать выходной директорией папку конкретного фаззинг-теста (out/FuzzXxx)
- использовать `bb-corpus suite`, но предварительно определить переменную `fuzz_in_dir` в конфигурационном файле (как в примере выше: out/FuzzXxx)
- копировать семплы другими средствами (rsync, cp)

<!-- [en] -->
Sample exporting works fine, but importing requires using of one of the following options:
- use `bb-corpus manual` and specify the folder of a specific fuzzing test (for example, out/FuzzXxx) as the output directory
- use `bb-corpus suite`, but pre-define the variable `fuzz_in_dir` in the config file (similarly: out/FuzzXxx)
- copy the samples by other means (rsync, cp)

<!-- [common] -->
</details>

<details>
<!-- [ru] -->
<summary>Подробности о работе bb-corpus</summary>

<!-- [en] -->
<summary>Details on how bb-corpus works</summary>

<!-- [ru] -->
Инструмент поддерживает импорт тестовых примеров из хранилища в папку фаззера и экспорт из папки фаззера в хранилище.<br>
Хранилище является примонтированной папкой и в свою очередь может быть каталогом Samba, NFS и т.д.<br>

Синхронизация происходит в два этапа:
1. Копирование (в случае импорта) или перемещение (в случае экспорта) из папки-источника во временную папку без создания дубликатов по содержимому (вычисляются хэш-суммы SHA1).
2. Минимизация семплов из временной папки в конечную папку с использованием инструментов фаззера (например, afl-cmin).

В конфигурационном файле bugbane.json должна быть объявлена переменная `fuzzer_type`.<br>
Для минимизации с использованием afl-cmin на диске должны присутствовать сборки тестируемого приложения. Наиболее предпочтительной сборкой для минимизации семплов является сборка в папке `laf`, т.к. она "различает" больше путей выполнения, но, если она отсутствует, то для минимизации используются другие сборки.

Имена результирующих файлов соответствуют хэш-сумме SHA1 их содержимого. При совпадении имён в конечной папке перезапись не происходит.

<!-- [en] -->
The tool supports importing test cases from the storage to the fuzzer working directory and exporting them from the fuzzer working directory back to the storage.<br>
The storage is just a mounted directory, which can in turn be some Samba share, an NFS drive, etc.<br>

Synchronization occurs in two stages:
1. Copying samples (if importing) or moving them (if exporting) from a source directory to a temporary folder without creating duplicates (SHA1 hash sum checks are in place).
2. Minimizing the samples in the temporary folder, saving results to a destination directory using fuzzer tools (such as afl-cmin)

The variable `fuzzer_type` must be defined in the configuration file bugbane.json.<br>
For afl-cmin minimization there must be builds of a tested app on disk. The most preferred build for minimizing samples is the one in the `laf` folder, as it "distinguishes" more execution paths, though, if this build is missing, bb-corpus uses the other builds for minimization.

The names of resulting files contain the SHA1 hash sum of their contents. If the destination directory already contains files with the matching names, no file overwriting occurs.

<!-- [common] -->
</details>

## bb-fuzz
<!-- [ru] -->
Запускает фаззинг тестируемого приложения на указанном количестве ядер, останавливает фаззинг при наступлении указанного условия остановки.<br>

Пример запуска:
<!-- [en] -->
Launches fuzzing of an app under test using a specified number of CPU cores, stops fuzzing when a specified stop condition occurs.<br>

Example usage:
<!-- [common] -->
```shell
FUZZ_DURATION=1800 bb-fuzz --max-cpus $(nproc) suite /fuzz
```
<!-- [ru] -->
В результате запускаются несколько экземпляров фаззера в сессии tmux.<br>
Инструмент bb-fuzz будет периодически печатать статистику работы фаззера, пока не обнаружит наступление условия остановки, в данном случае, пока не накопится время работы 1800 секунд (30 минут).<br>
Затем в папку /fuzz/screens будут сохранены дампы (текстовые представления) экранов фаззера. Эти дампы используются на следующих этапах приложениями bb-report или bb-screenshot для создания скриншотов.<br>

<!-- [en] -->
As a result, multiple fuzzer instances start running in a tmux session.<br>
The bb-fuzz tool will periodically print run statistics of the fuzzer until it detects the occurrence of a stop condition, in this case, until the duration of 1800 seconds (30 minutes) has passed.<br>
Then the tool saves fuzzer screen dumps (text representations) to the /fuzz/screens directory. The dumps are for the bb-report or bb-screenshot tools to create screenshots from in the next stages.<br>

<!-- [common] -->
<details>
<!-- [ru] -->
<summary>Подробности о работе bb-fuzz</summary>

<!-- [en] -->
<summary>Details on how bb-fuzz works</summary>

<!-- [ru] -->
Инструмент обнаруживает сборки приложения на диске и распределяет их по разным ядрам процессора.<br>
Алгоритм распределения сборок C/C++:
* сборкам с санитайзерами выделяется по одному ядру;
* вспомогательные сборки (AFL_LLVM_LAF_ALL, AFL_USE_CMPLOG) назначаются на определённую долю от доступных ядер;
* сборка basic (без санитайзеров) занимает остальные ядра;
* сборки для определения покрытия исходного кода в фаззинг-тестировании участие не принимают (см. bb-coverage).

<!-- [en] -->
The tool detects builds of a tested app on disk and distributes them across different processor cores.<br>
The distribution algorithm for C/C++ builds relies on the following rules:
* builds with sanitizers are allocated one core each;
* auxiliary builds (AFL_LLVM_LAF_ALL, AFL_USE_CMPLOG) are assigned to a certain proportion of the available cores;
* the basic build (without sanitizers) occupies the remaining cores;
* builds for source code coverage collection do not participate in fuzz testing (see bb-coverage).

<!-- [ru] -->
Для Go используется единственная сборка (в папке `gofuzz` или `gotest`), которая назначается на все доступные ядра.<br>
Для встроенного фаззера go test работа bb-fuzz завершается сразу же, как только будет обнаружен первый баг. Это вызвано особенностями работы фаззера. В случае отсутствия обнаруженных багов работа продолжается до наступления условия остановки.<br>

<!-- [en] -->
When fuzzing Go applications, there's only one build (in either `gofuzz` or `gotest` folder) which is allocated to all available cores.<br>
For the built-in Go fuzzer (go test) bb-fuzz exits on the first bug discovered. This is caused by the way the fuzzer works. If there are no detected bugs, the work continues as usual until a stop condition occurs.<br>

<!-- [ru] -->
В конфигурационном файле bugbane.json должны быть определены переменные `fuzzer_type`, `tested_binary_path`, `fuzz_cores`, `src_root`, `run_args`, `run_env` и `timeout`. Переменная `timeout` указывается в миллисекундах.<br>
На диске должны присутствовать сборки приложения, размещённые в папках, соответствующих названию сборки, точно так же, как их размещает инструмент bb-build.
Также на диске могут присутствовать файлы словарей с расширением ".dict" в папке "dictionaries". Они объединяются в один общий словарь, который передаётся фаззеру при условии поддержки со стороны фаззера.

<!-- [en] -->
The bugbane.json configuration file must define the variables `fuzzer_type`, `tested_binary_path`, `fuzz_cores`, `src_root`, `run_args`, `run_env`, and `timeout`. The variable `timeout` is specified in milliseconds.<br>
The builds of the app to test must exist on disk in folders corresponding to the build type, just as the bb-build tool places them.<br>
There may also be dictionary files with the ".dict" extension in the "dictionaries" folder. They are merged into one dictionary, which is provided for the fuzzer to use, subject to the support from the fuzzer.

<!-- [ru] -->
Доступные значения переменной `fuzzer_type`: AFL++, libFuzzer, go-fuzz, go-test.<br>
Переменная `tested_binary_path` содержит путь к тестируемому приложению относительно входной папки (где будет осуществлён поиск сборок). Пример: есть папка "build" с результатом сборки, исполняемый файл "app" сохранён по пути build/test/app, инструмент bb-build последовательно выполнил несколько сборок, каждый раз копируя папку "build" в путь /fuzz, т.е. получились пути /fuzz/basic/test/app, /fuzz/coverage/test/app и т.д. В этом случае переменная `tested_binary_path` должна равняться "test/app".<br>
Переменная `src_root` не используется напрямую, но без её указания потерпят неудачу утилиты, подлежащие запуску после bb-fuzz.<br>
`run_args` - строка с аргументами запуска тестируемого приложения. Переменная может включать последовательность "@@", вместо которой фаззер может подставлять тестовые примеры на вход тестируемой программе.<br>
Для встроенного фаззера Go переменная `run_args` обязана содержать опцию запуска `-test.fuzz` с указанием конкретного фаззинг-теста, например, `-test.fuzz=FuzzHttp`.<br>
`run_env` - переменные окружения, которые необходимо установить для запуска тестируемого приложения. Переменная LD_PRELOAD будет автоматически заменена на соответствующую переменную фаззера (например, AFL_PRELOAD для AFL++).<br>
Пример переменной `run_env` в конфигурационном файле:
<!-- [en] -->
The values available for the variable `fuzzer_type`: AFL++, libFuzzer, go-fuzz, go-test.<br>
The variable `tested_binary_path` holds the path to the tested app's binary relative to an input directory (where builds will be searched for). Example: imagine, there's a folder named "build" with the build results, executable is named "app" and is saved as build/test/app, the bb-build tool performed several builds each time copying the "build" folder to path /fuzz, that is, now there are paths /fuzz/basic/test/app, /fuzz/coverage/test/app, etc. In this case the `tested_binary_path` should be "test/app".<br>
The variable `src_root` is not used directly, but other BugBane tools running after bb-fuzz fail if the variable is missing.<br>
The `run_args` variable holds a string containing run arguments for the tested app. The variable may include the "@@" sequence, through which the fuzzer may provide input samples for the app.<br>
For the built-in Go fuzzer the variable `run_args` must contain the `-test.fuzz` launch option with a specific fuzz test, for instance, `-test.fuzz=FuzzHttp`.<br>
The `run_env` contains a dictionary of environment variables, required to fuzz the tested app. The env variable LD_PRELOAD is automatically converted to a corresponding fuzzer variable (such as AFL_PRELOAD for AFL++).<br>
Example of the `run_env` variable in the configuration file:
<!-- [common] -->
```json
"run_env": {
    "LD_PRELOAD": "/src/mylib.so",
    "ENABLE_FUZZ_TARGETS": "1"
}
```
<!-- [ru] -->
Доступные условия остановки фаззинг-тестирования:
* реальная продолжительность фаззинга достигла X секунд (затраченное время независимо от количества ядер / экземпляров фаззера);
* новые пути выполнения кода не обнаруживались в течение последних X секунд среди всех экземпляров фаззера.

<!-- [en] -->
The following stop conditions are available:
* actual fuzzing duration has reached X seconds (time spent regardless of the number of cores / fuzzer instances);
* no new code execution paths have been detected for the last X seconds among all instances of a fuzzer.

<!-- [ru] -->
Условие остановки задаётся с помощью переменных окружения:
* CERT_FUZZ_DURATION=X - X определяет количество секунд, в течение которых не должны обнаруживаться новые пути выполнения; переменная имеет наивысший приоритет, если установлены другие переменные;
* CERT_FUZZ_LEVEL=X - X определяет уровень контроля, что в свою очередь определяет время, в течение которого не должны обнаруживаться новые пути выполнения; допустимые значения X: 2, 3, 4; средний приоритет;
* FUZZ_DURATION=X - X определяет реальную продолжительность тестирования; низший приоритет.

Переменные CERT_FUZZ_\* подходят для сертификационных испытаний, FUZZ_\* - для использования в CI/CD.<br>
Если не объявлена ни одна из указанных переменных, используется FUZZ_DURATION=600.<br>

<!-- [en] -->
The stop condition is defined using the following environment variables:
* CERT_FUZZ_DURATION=X - X specifies the number of seconds without no new execution paths detected; this variable has the highest priority if other stop condition variables are set;
* CERT_FUZZ_LEVEL=X - X specifies so called "control level", which in turn defines the number of seconds without no new execution paths, available values of X are: 2, 3, 4; this variable has medium priority;
* FUZZ_DURATION=X - X specifies fuzzing duration (number of seconds); this variable has the lowest priority.

The CERT_FUZZ_\* variables are fit for software certification trials, and the FUZZ_\* variables are intended to be used in CI/CD.<br>
If none of the above variables are defined, then FUZZ_DURATION=600 is used implicitly.<br>

<!-- [ru] -->
Количество используемых ядер процессора определяется минимальным значением среди перечисленных:
1. Количество доступных в системе ядер.
2. Значение переменной `fuzz_cores` в файле конфигурации. Если значение не указано, будет выбрано 8 ядер.
3. Аргумент запуска `--max-cpus` (значение по умолчанию: 16).

Таким образом, ограничение на количество ядер накладывает как автор конфигурационного файла (предположительно, разработчик тестируемого ПО), так и конечный пользователь bb-fuzz (предположительно, команда AppSec).

<!-- [en] -->
The number of processor cores to use in fuzzing is determined by the minimal value of the following:
1. The number of CPU cores available in the OS.
2. The value of the `fuzz_cores` variable of the configuration file. If the variable is not specified, the value of 8 is used.
3. The value of the `--max-cpus` run argument, default is 16.

Thus, the number of processor cores is limited by both the author of the bugbane.json file (presumably, the developer of the tested application), and the end user of BugBane (presumably, an Application Security specialist).

<!-- [common] -->
</details>

## bb-coverage
<!-- [ru] -->
Собирает покрытие тестируемого приложения на семплах, сгенерированных фаззером.<br>

Пример запуска:
<!-- [en] -->
Collects coverage of a tested app using the test cases, generated during fuzz testing.<br>

Example usage:
<!-- [common] -->
```shell
bb-coverage suite /fuzz
```
<!-- [ru] -->
В результате в папке /fuzz/coverage_report появляются файлы отчёта о покрытии, в том числе /fuzz/coverage_report/index.html - главная страница отчёта.<br>
**Инструмент не работает для встроенного фаззера Go (go test).** Это вызвано особенностями работы фаззера.

<!-- [en] -->
As a result, coverage report files appear under the /fuzz/coverage_report directory, with the /fuzz/coverage_report/index.html being the main page of the report.<br>
**The tool does not work for the built-in Go fuzzer (go test).** This is due to the way the fuzzer works.

<!-- [common] -->
<details>
<!-- [ru] -->
<summary>Подробности о работе bb-coverage</summary>

<!-- [en] -->
<summary>Details on how bb-coverage works</summary>

<!-- [ru] -->
Работа инструмента для C/C++-приложений:
1. Запускает тестируемое приложение на семплах в директории синхронизации фаззера
2. Строит отчёт о покрытии

<!-- [en] -->
For C/C++ apps the tool does the following:
1. Runs an app under test on samples in the sync directory of a fuzzer
2. Generates a coverage report

<!-- [ru] -->
Для приложений на языке Go инструмент работает иначе:
1. Строит отчёт о покрытии с использованием данных, полученных при фаззинге с ключом запуска `-dumpcover` \*
2. Изменяет цвет фона в отчёте о покрытии с чёрного на белый

\* Инструмент bb-fuzz использует этот ключ.

<!-- [en] -->
For Go apps, the tool works differently:
1. Generates a coverage report using the coverage profiles, generated while fuzzing with the launch option `-dumpcover` \*
2. Changes the background color of the report from black to white

\* bb-fuzz uses this option.

<!-- [ru] -->
В конфигурационном файле bugbane.json должны быть объявлены переменные `tested_binary_path`, `run_args`, `run_env`, `coverage_type`, `fuzzer_type`, `fuzz_sync_dir` и `src_root`.<br>
Переменная `coverage_type` заполняется приложением bb-build и соответствует использованному сборщику.<br>
`src_root` - путь к исходному коду тестируемого приложения на момент выполнения сборок; путь не обязан реально существовать в файловой системе: если директория не существует, отчёт о покрытии будет содержать проценты, но не исходный код.

<!-- [en] -->
The configuration file bugbane.json should define the variables `tested_binary_path`, `run_args`, `run_env`, `coverage_type`, `fuzzer_type`, `fuzz_sync_dir`, and `src_root`.<br>
The `coverage_type` variable gets set by bb-build and matches the builder type used there.<br>
The `src_root` variable holds the path to the source code of the tested app, which existed during the build process; the path does not have to actually exist on the file system during coverage collection: if the directory doesn't exist, then resulting coverage report shows coverage percentages, but not the code itself.

<!-- [ru] -->
Возможные значения `coverage_type`
| coverage_type | Описание |
|-|-|
| lcov | Для целей, собранных компиляторами GCC с флагом `--coverage` |
| lcov-llvm | Для целей, собранных компиляторами LLVM с флагом `--coverage` |
| go-tool-cover | Для целей на языке Go |

<!-- [en] -->
Possible values of the `coverage_type` variable
| coverage_type | Description |
|-|-|
| lcov | For targets built with GCC compilers and the `--coverage` flag |
| lcov-llvm | For targets built with LLVM compilers and the `--coverage` flag |
| go-tool-cover | For Go targets |

<!-- [common] -->
</details>

## bb-reproduce
<!-- [ru] -->
Воспроизводит обнаруженные фаззером падения и зависания и обобщает результаты работы фаззера.<br>

Пример запуска:
<!-- [en] -->
Reproduces fuzzer-discovered crashes and hangs and summarizes the results of a fuzzing campaign.<br>

Example usage:
<!-- [common] -->
```shell
bb-reproduce suite /fuzz
```

<!-- [ru] -->
В результате формируется файл /fuzz/bb_results.json, содержащий статистику работы фаззера и сведения о воспроизводимых багах. Семплы, соответствующие воспроизводимым багам, сохраняются в папке /fuzz/bug_samples.<br>

<!-- [en] -->
This generates the file /fuzz/bb_results.json, containing the fuzzer statistics and information about reproducible bugs. Test cases for the bugs reproduced are saved under the /fuzz/bug_samples directory.<br>

<!-- [common] -->
<details>
<!-- [ru] -->
<summary>Подробности о работе bb-reproduce</summary>

<!-- [en] -->
<summary>Details on how bb-reproduce works</summary>

<!-- [ru] -->
Инструмент bb-reproduce выполняет следующие действия:
1. Получает общую статистику работы фаззеров
2. Минимизирует падения и зависания путём их воспроизведения
3. Составляет информацию о каждом уникальном воспроизводимом баге
4. Формирует JSON-файл со статистикой и данными о багах
5. Сохраняет на диск тестовые примеры, приводящие к воспроизводимым падениям и зависаниям

<!-- [en] -->
The bb-reproduce tool does the following:
1. Collects the overall statistics of fuzzers' operation
2. Minimizes crashes and hangs by reproducing them
3. Records information about each unique reproducible bug
4. Generates a JSON file with the stats and the bugs data
5. Saves test cases resulting in reproducible crashes and hangs to disk

<!-- [ru] -->
Для каждого бага сохраняются такие сведения как заголовок issue/бага, место возникновения бага в исходном коде, команда запуска с конкретным семплом, вывод приложения (stdout+stderr), переменные окружения и т.д.<br>
Поддерживаются цели, инструментированные с помощью [SharpFuzz](https://github.com/Metalnem/sharpfuzz).<br>

<!-- [en] -->
The data saved for each reproducible bug includes the issue/bug title, the location of the bug in the source code, the run command with a particular test sample, the app output (stdout+stderr), the environment variables, etc.<br>
Targets instrumented with [SharpFuzz](https://github.com/Metalnem/sharpfuzz) are also supported by the tool.

<!-- [ru] -->
В конфигурационном файле bugbane.json должны быть определены переменные `src_root`, `fuzz_sync_dir`, `fuzzer_type`, `reproduce_specs`, `run_args` и `run_env`. Переменные `fuzz_sync_dir` и `reproduce_specs` добавляются инструментом bb-fuzz.<br>
`fuzz_sync_dir` - директория синхронизации фаззера; bb-fuzz использует директорию "out".<br>
`src_root` - путь к исходному коду тестируемого приложения на момент выполнения сборок; не обязан реально существовать в файловой системе, используется для более точного определения места падений/зависаний в исходном коде.<br>
`reproduce_specs` - словарь, определяющий тип фаззера, и задающий соответствие между сборками приложения и папками, на которых требуется выполнить воспроизведение:
<!-- [en] -->
The bugbane.json configuration file must define the variables `src_root`, `fuzz_sync_dir`, `fuzzer_type`, `reproduce_specs`, `run_args`, and `run_env`. The variables `fuzz_sync_dir` and `reproduce_specs` are usually set by the bb-fuzz tool.<br>
The `fuzz_sync_dir` contains the path to the fuzzer synchronization directory; bb-fuzz uses the "out" directory.<br>
The `src_root` is the root directory of the tested app's source code as it was at the time of build; the path does not have to exist on the file system as the variable is only used for better precision when locating the crashing/hanging line in the source code.<br>
The `reproduce_specs` is a JSON dictionary, specifying the fuzzer type and mapping the builds of the tested app to the folders, on which to reproduce bugs:
<!-- [common] -->
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
<!-- [ru] -->
В данном случае сборка basic (/fuzz/basic/app) будет запущена на семплах `/fuzz/out/test1/{crashes,hangs}/id*`, а сборка ubsan (/fuzz/ubsan/app) - на семплах `/fuzz/out/test{2,3}/{crashes,hangs}/id*`.<br>

<!-- [en] -->
In the above example the `basic` build (/fuzz/basic/app) will be run with the samples matching the pattern `/fuzz/out/test1/{crashes,hangs}/id*`, and for the `ubsan` build (/fuzz/ubsan/app) the pattern will be `/fuzz/out/test{2,3}/{crashes,hangs}/id*`.<br>

<!-- [ru] -->
При каждом запуске анализируется вывод приложения в терминал, например, инструмент ищет сообщения санитайзеров. Каждый баг воспроизводится до успешного воспроизведения, но не более N раз. Число N определяется аргументом запуска bb-reproduce `--num-reruns` (значение по умолчанию: 3). Если при воспроизведении падения не обнаруживается стек вызовов, приложение запускается под отладчиком gdb. Зависания воспроизводятся сразу под отладчиком gdb.<br>

<!-- [en] -->
The output of the tested app is analyzed on each reproduce try, for example, the tool searches for sanitizer messages. Each bug sample is tried until a successful bug detection, but not more than N times. The number N is defined by the `--num-reruns` argument of bb-reproduce (the default value is 3). When trying a crashing sample, if the app does not produce the stack trace, then the app is ran under the gdb debugger. Hangs are always reproduced under gdb.<br>

<!-- [common] -->
</details>

<!-- [ru] -->
### Просмотр информации о багах
<!-- [en] -->
### Viewing the bugs information
<!-- [ru] -->
Информацию о найденных багах можно вывести в терминал с использованием утилиты jq (устанавливается отдельно).<br>
Это позволяет просматривать и заводить баги вручную, например, если не используется система Defect Dojo или утилита bb-send.<br>

Простой текстовый формат для удобного просмотра в терминале:
<!-- [en] -->
Information about the bugs discovered may be displayed in the terminal with the jq utility (installed separately).<br>
This allows you to view and report bugs manually, for example, if you don't use Defect Dojo or the bb-send tool.<br>

To get a simple text representation for viewing in the terminal use the command:
<!-- [common] -->
```shell
jq '.issue_cards[] | "-" * 79, .title, .reproduce_cmd, .output, "Saved sample name", .sample, ""' -rM bb_results.json
```

<!-- [ru] -->
Готовое описание issue для GitHub:
<!-- [en] -->
To get an issue text ready for GitHub use the following:
<!-- [common] -->
````shell
jq '.issue_cards[] | "## \(.title)", "Originally reproduced by executing: \n```shell\n\(.reproduce_cmd)\n```", "Output:\n```\n\(.output)```", "Saved sample name: \(.sample)", ""' -rM bb_results.json
````

<!-- [ru] -->
Готовое описание issue для Jira:
<!-- [en] -->
To get an issue text ready for Jira use this:
<!-- [common] -->
````shell
jq '.issue_cards[] | "h1. \(.title)", "Originally reproduced by executing: \n{noformat}\n\(.reproduce_cmd)\n{noformat}", "Output:\n{noformat}\n\(.output){noformat}", "Saved sample name: \(.sample)", ""' -rM bb_results.json
````

<!-- [ru] -->
Рекомендуется заводить issue на каждый отдельный баг, поскольку баги уже прошли дедупликацию с помощью bb-reproduce и с высокой долей вероятности являются уникальными.<br>
Если предпочтительнее создавать одно issue на все обнаруженные баги, то к нему достаточно приложить архив с директорией `bug_samples`.<br>

<!-- [en] -->
It's recommended to create an issue for each separate bug, as the bugs have already been deduplicated by bb-reproduce and are already unique with high probability.<br>
If it's preferred to create a single issue for all discovered bugs, then it's sufficient to attach to it an archive with the `bug_samples` directory.<br>

<!-- [common] -->
## bb-send
<!-- [ru] -->
Заводит воспроизводимые баги в системе управления уязвимостями Defect Dojo.<br>
Входные данные берутся из файла bb_results.json, полученного в результате работы инструмента bb-reproduce.<br>
Файл bugbane.json не используется.<br>

Пример запуска:
<!-- [en] -->
Puts reproducible bugs in the Defect Dojo vulnerability management system.<br>
The input data is taken from the bb_results.json file, created by the bb-reproduce tool.<br>
The bugbane.json file is not used.<br>

Example usage:
<!-- [common] -->
```shell
export BB_DEFECT_DOJO_SECRET="DD_TOKEN"
bb-send --host https://dojo.local \
    --user-name ci_fuzz_user --user-id 2 \
    --engagement 1 --test-type 141 \
    --results-file bb_results.json
```
<!-- [ru] -->
В результате на сервере Defect Dojo по адресу `https://dojo.local` будет создан новый тест с типом 141 в engagement 1. Каждый баг будет заведён отдельно в пределах нового теста.

<!-- [en] -->
As a result, a new test appears with the test type 141 in the engagement having the id 1 on the Defect Dojo server hosted at `https://dojo.local`. Each bug is created separately from the other ones in this new test.

<!-- [common] -->
<details>
<!-- [ru] -->
<summary>Описание некоторых аргументов запуска bb-send</summary>

<!-- [en] -->
<summary>Details on some of the bb-send run options</summary>

<!-- [ru] -->
Здесь и далее в качестве адреса сервера Defect Dojo используется `https://dojo.local`.<br>
`--user-id`: id указанного в `--user-name` пользователя; можно посмотреть в адресной строке Defect Dojo, выбрав нужного пользователя на странице `https://dojo.local/user`.<br>
`--engagement`: engagement id; также можно посмотреть в адресной строке в браузере (выбрать нужный engagement на странице `https://dojo.local/engagement`).<br>
`--test-type`: id вида теста; брать также из адресной строки (выбрать нужный тест на странице `https://dojo.local/test_type`).<br>
`--token`: ключ API; берётся из Defect Dojo по ссылке: `https://dojo.local/api/key-v2` (нужно быть авторизованным от имени, указанного в `--user-name`, ключ нужен из раздела "Your current API key is ....").<br>
Рекомендуется вместо опций `--user-name` и `--token` использовать переменные окружения `BB_DEFECT_DOJO_LOGIN` и `BB_DEFECT_DOJO_SECRET`.<br>

<!-- [en] -->
Hereinafter `https://dojo.local` is used as the address of the Defect Dojo server.<br>
`--user-id`: id of the user specified in the `--user-name` option; may be taken from the Defect Dojo's url, while desired user is selected on the page `https://dojo.local/user`.<br>
`--engagement`: engagement id; may also be taken from the engagement url (select one on the page `https://dojo.local/engagement`).<br>
`--test-type`: test type id; also comes from the url (select required test type on the page `https://dojo.local/test_type`).<br>
`--token`: API key; copied from the page `https://dojo.local/api/key-v2` (you need to be authorized with the name specified in the `--user-name` option, you need the API key from the part, starting with "Your current API key is ....").<br>
You are advised to use the env variables `BB_DEFECT_DOJO_LOGIN` and `BB_DEFECT_DOJO_SECRET` instead of the args `--user-name` and `--token`.<br>

<!-- [ru] -->
Если подлинность сертификата сервера Defect Dojo не может быть проверена, то следует добавить аргумент запуска `--no-ssl`.

<!-- [en] -->
If the authenticity of the Defect Dojo server certificate cannot be verified, the `--no-ssl` option should be added.

<!-- [common] -->
</details>

## bb-report
<!-- [ru] -->
Создаёт отчёт о выполненном фаззинг-тестировании в формате Markdown на основе указанного шаблона Jinja2.<br>
По умолчанию используется шаблон с описанием процесса фаззинга на русском языке и включает команды, использованные для запуска фаззеров, скриншоты фаззеров, статистику работы и т.д.<br>

<!-- [en] -->
Generates a Markdown fuzz test report based on a specified Jinja2 template.<br>
The default template contains textual description of the fuzzing process in Russian and includes the commands used to start fuzzers, the fuzzer screenshots, some of the stats, etc.<br>

<!-- [ru] -->
Инструмент создаёт скриншоты:
1. Окон фаззера - из дампов tmux, сохранённых инструментом bb-fuzz
2. Главной страницы отчёта о покрытии кода, созданного инструментов bb-coverage

<!-- [en] -->
The tool creates screenshots of the following:
1. the fuzzer - made from the tmux dumps, saved by the bb-fuzz tool
2. the main page of the coverage report, which was generated by the bb-coverage tool

<!-- [ru] -->
Скриншоты сохраняются в папку screenshots и вставляются в отчёт в виде ссылок.<br>
В файле конфигурации bugbane.json должны быть объявлены переменные `fuzzer_type`, `coverage_type` и `fuzz_sync_dir`.<br>

Пример запуска:
<!-- [en] -->
The screenshots are saved to the "screenshots" folder and inserted into the report as links.<br>
The configuration file bugbane.json should define the variables `fuzzer_type`, `coverage_type`, and `fuzz_sync_dir`.<br>

Example usage:
<!-- [common] -->
```shell
bb-report --name myapp_fuzz suite /fuzz
```

<!-- [ru] -->
Запуск с использованием Selenium:
<!-- [en] -->
Example usage with Selenium:
<!-- [common] -->
```shell
bb-report --html-screener selenium --name myapp_fuzz suite /fuzz
```

<!-- [ru] -->
В результате в папке /fuzz появляется директория screenshots с изображениями и файл с отчётом `myapp_fuzz.md`.<br>

Для создания документа в формате DOCX можно использовать утилиту pandoc (устанавливается отдельно):
<!-- [en] -->
As a result, the screenshots folder appears in the /fuzz directory with the images and the report file `myapp_fuzz.md`.<br>

In order to create a report in the DOCX format you can use the pandoc tool (installed separately):
<!-- [common] -->
```shell
pandoc -f markdown -t docx myapp_fuzz.md -o myapp_fuzz.docx
```

## bb-screenshot
<!-- [ru] -->
Создаёт скриншоты из указанных пользователем HTML-файлов, текстовых файлов, а также из файлов, содержащих ANSI-последовательности. Изображения создаются так же, как в приложении bb-report, но пользователь может указать имена входного и выходного файлов.<br>

Примеры запуска:
<!-- [en] -->
Creates images from a user-provided HTML files, simple text files, or files containing ANSI sequences. The images are made in the same way, as in the bb-report tool, but the user may specify input and output paths.<br>

Usage examples:
<!-- [common] -->
```shell
bb-screenshot -S pango -i tmux_dump.txt -o tmux_screenshot.png
bb-screenshot -S weasyprint -i index.html -o coverage.png
bb-screenshot -S selenium -i index.html -o coverage2.png
```

<!-- [ru] -->
# Развитие

<!-- [en] -->
# Improvements

<!-- [ru] -->
Планы по улучшению BugBane:
* поддержка других фаззеров
* добавление других утилит
* генерация отчётов в других форматах и по другим шаблонам

<!-- [en] -->
Future plans for BugBane:
* add support for more fuzzers
* add more tools
* add more report templates and support different reporting formats

<!-- [ru] -->
# Для разработчиков
<!-- [en] -->
# For developers
<!-- [ru] -->
Установка в режиме editable в виртуальное окружение:
<!-- [en] -->
Install the project in editable mode using a virtual environment:
<!-- [common] -->
```
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

<!-- [ru] -->
Запуск юнит-тестов pytest:
<!-- [en] -->
Run the pytest suite:
<!-- [common] -->
```
pytest
```

<!-- [ru] -->
# Благодарности
<!-- [en] -->
# Acknowledgements
<!-- [ru] -->
Спасибо всем участникам проекта!

Отдельные благодарности:
- [Илья Уразбахтин](https://github.com/donyshow): идеи, консультации, менторство.
<!-- [en] -->
Thank you to everyone involved in the project!

Special thanks:
- [Ilya Urazbakhtin](https://github.com/donyshow): ideas, consultations, mentoring.
