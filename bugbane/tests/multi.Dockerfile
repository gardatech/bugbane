# CI-like testing with multiple fuzz targets and coverage collection of BugBane tools
# docker build -t bugbane_ci_test -f bugbane/tests/multi.Dockerfile .

FROM archlinux AS base
RUN pacman --noconfirm --needed -Syu \
        vim nano tmux bash-completion python python-pip \
        base-devel git cmake gdb strace ltrace diffutils \
        clang llvm lld lib32-gcc-libs \
        lcov cloc \
        jq moreutils \
        pango ttf-liberation \
        geckodriver firefox && \
    fc-cache

RUN sh -c 'echo set encoding=utf-8 > /root/.vimrc' && \
    echo '. /usr/share/bash-completion/bash_completion' >> ~/.bashrc && \
    echo "export PS1='"'[bugbane \h] \w \$ '"'" >> ~/.bashrc && \
    git config --global advice.detachedHead false

ARG GIT_ANSIFILTER_TAG="2.18"
RUN git clone --depth=1 https://gitlab.com/saalen/ansifilter.git -b ${GIT_ANSIFILTER_TAG} /ansifilter && \
    cd /ansifilter && make && make install && cd / && rm -rf /ansifilter

ARG GIT_AFLPP_TAG="4.00c"
RUN git clone --depth 1 https://github.com/AFLplusplus/AFLplusplus -b ${GIT_AFLPP_TAG} /AFLplusplus
RUN cd /AFLplusplus && \
    # unmute ubsan messages
    sed -i 's|cc_params\[cc_par_cnt++\] = "-fsanitize-undefined-trap-on-error";||g' ./src/afl-cc.c && \
    # unmute cfisan messages
    sed -i 's|"-fsanitize=cfi";|"-fsanitize=cfi";\n    cc_params\[cc_par_cnt++\] = "-fno-sanitize-trap=cfi";|g' ./src/afl-cc.c && \
    # disable G1 drawing mode for AFL++ status screen
    sed -i 's|#define FANCY_BOXES|// #define FANCY_BOXES|g' ./include/config.h && \
    # more frequent updates of fuzzer_stats files
    sed -i 's|#define STATS_UPDATE_SEC .*$|#define STATS_UPDATE_SEC 5|g' ./include/config.h && \
    make source-only && make install

# cache BugBane deps
RUN pip3 install \
        beautifulsoup4 lxml Jinja2 requests selenium WeasyPrint==52.5 build wheel \
        pytest pytest-mock coverage

FROM base AS common_prep

# re2 is used as both AFL++ and libFuzzer targets
ARG GIT_RE2_TAG="2021-11-01"
RUN git clone --depth 1 https://github.com/google/re2.git -b ${GIT_RE2_TAG} /src/re2



FROM common_prep AS bugbane_tools

COPY . /bugbane

# NOTE: further changes to workdir break coverage collection
WORKDIR /bugbane

RUN python3 -m pip install -e .[all] && \
    pytest && echo "Tests: OK" && \
    find /bugbane -type f -name ".coverage" -delete

ENV COVERAGE_RCFILE=/bugbane/setup.cfg
ENV FUZZ_DURATION=12


FROM bugbane_tools AS configure_aflpp_target

RUN echo -e '\n\
export CXX="${CXX:=afl-clang-fast++}" &&\n\
mkdir -p build &&\n\
make clean &&\n\
make -j obj/libre2.a &&\n\
$CXX $CXXFLAGS --std=c++11 -I. re2/fuzzing/re2_fuzzer.cc /AFLplusplus/libAFLDriver.a obj/libre2.a -lpthread -o build/re2_fuzzer' \
        > /src/re2/aflpp_build.sh && \
    chmod +x /src/re2/aflpp_build.sh

RUN echo -e '{\n\
    "fuzzing": {\n\
        "os_name": "Arch Linux",\n\
        "os_version": "Rolling",\n\
\n\
        "product_name": "Google RE2",\n\
        "product_version": "'${GIT_RE2_TAG}'",\n\
        "module_name": "BugBane CI-test for AFL++",\n\
        "application_name": "re2",\n\
\n\
        "is_library": true,\n\
        "is_open_source": true,\n\
        "language": [\n\
            "C++"\n\
        ],\n\
        "parse_format": [\n\
            "RegExp"\n\
        ],\n\
        "tested_source_file": "re2_fuzzer.cc",\n\
        "tested_source_function": "TestOneInput",\n\
        "build_cmd": "./aflpp_build.sh",\n\
        "build_root": "./build",\n\
        "tested_binary_path": "re2_fuzzer",\n\
        "builder_type": "AFL++LLVM",\n\
        "fuzzer_type": "AFL++",\n\
\n\
        "run_args": null,\n\
        "run_env": null,\n\
\n\
        "fuzz_cores": 6,\n\
        "sanitizers": [\n\
            "ASAN", "UBSAN"\n\
        ]\n\
    }\n\
}' > /src/re2/bugbane.json


FROM configure_aflpp_target AS test_aflpp
RUN coverage run -a -m bugbane build -vv -i /src/re2 -o /fuzz/aflpp && \
    egrep '^\$ ' /fuzz/aflpp/build.log | cut -c 3- > /fuzz/aflpp/build.cmds && \
    jq '.fuzzing += {"build_cmd": "/fuzz/aflpp/build.cmds"}' /src/re2/bugbane.json \
        > /fuzz/aflpp/bugbane.json && \
    date

RUN : \
    && mkdir -p /fuzz/aflpp/dictionaries \
    && cp -t /fuzz/aflpp/dictionaries \
            /AFLplusplus/dictionaries/regexp.dict \
            /AFLplusplus/dictionaries/xml*.dict \
    && :

RUN coverage run -a -m bugbane fuzz -vv --suite /fuzz/aflpp && date
RUN coverage run -a -m bugbane coverage -vv suite /fuzz/aflpp && date
RUN coverage run -a -m bugbane reproduce -vv suite /fuzz/aflpp && date
RUN coverage run -a -m bugbane report -vv --name report_aflpp suite /fuzz/aflpp && date

# taking too long for CI:
# RUN coverage run -a -m bugbane corpus -vv suite /fuzz/aflpp export-to /storage/aflpp



# FROM bugbane_tools AS configure_libfuzzer_target
FROM test_aflpp AS configure_libfuzzer_target
RUN sed -i '0,/#include/ s||#include <limits>\n#include|g' /src/re2/re2/fuzzing/re2_fuzzer.cc
RUN echo -e 'export CXX="${CXX:=clang++}" &&\n\
mkdir -p build\n\
rm -rf build/*\n\
make clean &&\n\
make -j obj/libre2.a &&\n\
$CXX $CXXFLAGS --std=c++11 -I. re2/fuzzing/re2_fuzzer.cc -fsanitize=fuzzer obj/libre2.a -o build/re2_fuzzer' \
        > /src/re2/fuzz_build.sh && \
    chmod +x /src/re2/fuzz_build.sh

# overwrite possibly changed bugbane.json:
RUN echo -e '{\n\
    "fuzzing": {\n\
        "os_name": "Arch Linux",\n\
        "os_version": "Rolling",\n\
\n\
        "product_name": "Google RE2",\n\
        "product_version": "'${GIT_RE2_TAG}'",\n\
        "module_name": "BugBane CI-test for libFuzzer",\n\
        "application_name": "re2",\n\
\n\
        "is_library": true,\n\
        "is_open_source": true,\n\
        "language": [\n\
            "C++"\n\
        ],\n\
        "parse_format": [\n\
            "RegExp"\n\
        ],\n\
        "tested_source_file": "re2_fuzzer.cc",\n\
        "tested_source_function": "TestOneInput",\n\
        "build_cmd": "./fuzz_build.sh",\n\
        "build_root": "./build",\n\
        "tested_binary_path": "re2_fuzzer",\n\
        "builder_type": "libFuzzer",\n\
        "fuzzer_type": "libFuzzer",\n\
\n\
        "run_args": "@@",\n\
        "run_env": null,\n\
\n\
        "fuzz_cores": 6,\n\
        "sanitizers": [\n\
            "ASAN", "UBSAN"\n\
        ]\n\
    }\n\
}' > /src/re2/bugbane.json


FROM configure_libfuzzer_target AS test_libfuzzer
RUN coverage run -a -m bugbane build -vv -i /src/re2 -o /fuzz/libfuzzer && \
    egrep '^\$ ' /fuzz/libfuzzer/build.log | cut -c 3- > /fuzz/libfuzzer/build.cmds && \
    jq '.fuzzing += {"build_cmd": "/fuzz/libfuzzer/build.cmds"}' /src/re2/bugbane.json \
        > /fuzz/libfuzzer/bugbane.json && \
    date

RUN : \
    && mkdir -p /fuzz/libfuzzer/dictionaries \
    && cp -t /fuzz/libfuzzer/dictionaries \
            /AFLplusplus/dictionaries/regexp.dict \
            /AFLplusplus/dictionaries/xml*.dict \
    && :

RUN coverage run -a -m bugbane fuzz -vv --suite /fuzz/libfuzzer && date
RUN coverage run -a -m bugbane coverage -vv suite /fuzz/libfuzzer && date
RUN coverage run -a -m bugbane reproduce -vv suite /fuzz/libfuzzer && date
RUN coverage run -a -m \
        bugbane report -vv --html-screener selenium \
            --name report_libfuzzer suite /fuzz/libfuzzer && date

# taking too long for CI:
# RUN coverage run -a -m bugbane corpus -vv suite /fuzz/libfuzzer export-to /storage/libfuzzer


FROM test_libfuzzer AS dev_info
RUN cloc /bugbane/bugbane && coverage report --include "*/bugbane/*" && \
    coverage run -a -m pytest -q && coverage report --include "*/bugbane/*"
