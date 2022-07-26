# CI-like testing with multiple fuzz targets and coverage collection of BugBane tools
# NOTE: need at least 2 cores available to container.
# NOTE: BuildKit is required to build image from this Dockerfile:
#   docker build -t bugbane_integration_test -f bugbane/tests/integration.Dockerfile .
# While changing fuzzme project use this:
#   docker build -t bugbane_integration_test --build-arg local_fuzzme=true -f bugbane/tests/integration.Dockerfile ..

ARG local_fuzzme=false

FROM archlinux AS base
RUN : \
    && pacman --noconfirm --needed -Syu \
        vim nano tmux bash-completion python python-pip \
        base-devel git cmake gdb strace ltrace diffutils \
        clang llvm lld lib32-gcc-libs \
        go \
        lcov cloc \
        jq moreutils \
        pango ttf-liberation \
        geckodriver firefox \
    && fc-cache \
    && :

RUN : \
    && sh -c 'echo set encoding=utf-8 > /root/.vimrc' \
    && echo '. /usr/share/bash-completion/bash_completion' >> ~/.bashrc \
    && echo "export PS1='"'[bugbane \h] \w \$ '"'" >> ~/.bashrc \
    && git config --global advice.detachedHead false \
    && :


# go-fuzz with deps
ENV GOPATH /root/go
ENV GO111MODULE=off
WORKDIR $GOPATH
ENV PATH $PATH:/root/.go/bin:$GOPATH/bin

# RUN go version && \
#     go get -u golang.org/dl/gotip && \
#     gotip download && gotip version

RUN go get -u \
    github.com/dvyukov/go-fuzz/go-fuzz \
    github.com/dvyukov/go-fuzz/go-fuzz-build


# AFL++
ARG GIT_AFLPP_TAG="4.01c"
ARG AFLPP_SRC_DIR="/AFLplusplus"
ENV AFLPP_SRC_DIR=${AFLPP_SRC_DIR}
RUN : \
    && git clone --depth 1 https://github.com/AFLplusplus/AFLplusplus \
        -b ${GIT_AFLPP_TAG} ${AFLPP_SRC_DIR} \
    && cd ${AFLPP_SRC_DIR} \
    && sed -i 's|cc_params\[cc_par_cnt++\] = "-fsanitize-undefined-trap-on-error";||g' ./src/afl-cc.c \
    && sed -i 's|"-fsanitize=cfi";|"-fsanitize=cfi";\n    cc_params\[cc_par_cnt++\] = "-fno-sanitize-trap=cfi";|g' ./src/afl-cc.c \
    && sed -i 's|#define FANCY_BOXES|// #define FANCY_BOXES|g' ./include/config.h \
    && sed -i 's|#define STATS_UPDATE_SEC .*$|#define STATS_UPDATE_SEC 5|g' ./include/config.h \
    && export NO_NYX=1 \
    && export CC=clang CXX=clang++ \
    && make source-only \
    && make install \
    && :


ARG GIT_ANSIFILTER_TAG="2.18"
ARG ANSIFILTER_SRC_DIR="/ansifilter"
RUN : \
    && git clone --depth=1 https://gitlab.com/saalen/ansifilter.git \
        -b ${GIT_ANSIFILTER_TAG} ${ANSIFILTER_SRC_DIR} \
    && cd ${ANSIFILTER_SRC_DIR} \
    && env CC=clang CXX=clang++ make \
    && make install \
    && cd / \
    && rm -rf ${ANSIFILTER_SRC_DIR} \
    && :

# cache BugBane deps
RUN pip3 install \
        beautifulsoup4 lxml Jinja2 requests selenium WeasyPrint==52.5 build wheel \
        pytest pytest-mock coverage

ARG SRC="/src"
ENV SRC=${SRC}



# BuildKit magic to install fuzzme either from github or from local directory.
# This also affects bugbane source path (relative to docker build context)
FROM base AS bugbane_local_fuzzme_true
ARG BB_PATH="bugbane"
COPY fuzzme ${SRC}

FROM base AS bugbane_local_fuzzme_false
ARG BB_PATH="."
ENV FUZZME_FROM_GIT=1

FROM bugbane_local_fuzzme_${local_fuzzme} AS bugbane
COPY ${BB_PATH} /bugbane

# NOTE: further changes to workdir break coverage collection
WORKDIR /bugbane

RUN : \
    && python3 -m pip install -e .[all] \
    && coverage run -m pytest \
    && echo "UNIT COVERAGE:" \
    && coverage report --include "*/bugbane/*" \
    && find /bugbane -type f -name ".coverage" -delete \
    && :

ENV COVERAGE_RCFILE=/bugbane/setup.cfg
ENV FUZZ_DURATION=12



FROM bugbane AS test

ENV AFL_SKIP_CPUFREQ=1

ENV FUZZ="/fuzz"
RUN mkdir -p ${FUZZ}/{libFuzzer,aflpp,go-fuzz}

CMD : \
    && if [ ! -z $FUZZME_FROM_GIT ] ; then git clone https://github.com/gardatech/fuzzme $SRC; fi \
    && : LIBFUZZER : \
    && jq '.fuzzing += { "builder_type": "libFuzzer", "fuzzer_type": "libFuzzer" }' $SRC/cpp/bugbane.json \
        | sponge $SRC/cpp/bugbane.json \
    && coverage run -a -m bugbane build -vv -i ${SRC}/cpp -o ${FUZZ}/libFuzzer \
    && jq ".fuzzing += { \"build_cmd\": \"${FUZZ}/libFuzzer/build.cmds\" }" $SRC/cpp/bugbane.json \
        > ${FUZZ}/libFuzzer/bugbane.json \
    && mkdir -p ${FUZZ}/libFuzzer/dictionaries \
    && cp -t ${FUZZ}/libFuzzer/dictionaries \
            ${AFLPP_SRC_DIR}/dictionaries/regexp.dict \
            ${AFLPP_SRC_DIR}/dictionaries/xml*.dict \
    && coverage run -a -m bugbane fuzz -vv suite ${FUZZ}/libFuzzer \
    && coverage run -a -m bugbane coverage -vv suite ${FUZZ}/libFuzzer \
    && coverage run -a -m bugbane reproduce -vv suite ${FUZZ}/libFuzzer \
    && rm -rf /storage/libFuzzer \
    && coverage run -a -m bugbane corpus -vv suite ${FUZZ}/libFuzzer export-to /storage/libFuzzer \
    && coverage run -a -m bugbane report -vv --name report_libFuzzer suite ${FUZZ}/libFuzzer \
    && cd ${FUZZ}/libFuzzer \
    && cp -t /storage/libFuzzer -r \
        *.md coverage_report \
        screens screenshots \
        *.json *.log \
        bug_samples dictionaries \
        2>/dev/null || : \
    && cd - \
    && : AFL++ : \
    && jq '.fuzzing += { "builder_type": "AFL++LLVM", "fuzzer_type": "AFL++", "run_args": "@@" }' $SRC/cpp/bugbane.json \
        | sponge $SRC/cpp/bugbane.json \
    && coverage run -a -m bugbane build -vv -i ${SRC}/cpp -o ${FUZZ}/aflpp \
    && egrep '^\$ ' ${FUZZ}/aflpp/build.log | cut -c 3- > ${FUZZ}/aflpp/build.cmds \
    && jq ".fuzzing += { \"build_cmd\": \"${FUZZ}/aflpp/build.cmds\" }" $SRC/cpp/bugbane.json \
        > ${FUZZ}/aflpp/bugbane.json \
    && mkdir -p ${FUZZ}/aflpp/dictionaries \
    && cp -t ${FUZZ}/aflpp/dictionaries \
            ${AFLPP_SRC_DIR}/dictionaries/regexp.dict \
            ${AFLPP_SRC_DIR}/dictionaries/xml*.dict \
    && coverage run -a -m bugbane fuzz -vv suite ${FUZZ}/aflpp \
    && coverage run -a -m bugbane coverage -vv suite ${FUZZ}/aflpp \
    && coverage run -a -m bugbane reproduce -vv suite ${FUZZ}/aflpp \
    && rm -rf /storage/aflpp \
    && coverage run -a -m bugbane corpus -vv suite ${FUZZ}/aflpp export-to /storage/aflpp \
    && coverage run -a -m bugbane report -vv --html-screener selenium \
        --name report_aflpp suite ${FUZZ}/aflpp \
    && cd ${FUZZ}/aflpp \
    && cp -t /storage/aflpp -r \
        *.md coverage_report \
        screens screenshots \
        *.json *.log \
        bug_samples dictionaries \
        2>/dev/null || : \
    && cd - \
    && : GO-FUZZ : \
    && export FUZZ_DURATION=30 \
    && cd ${SRC}/go && ./build.sh \
    && mkdir -p ${FUZZ}/go-fuzz/gofuzz \
    && mv build/*.zip ${FUZZ}/go-fuzz/gofuzz/ \
    && cp ${SRC}/go/bugbane.json ${FUZZ}/go-fuzz \
    && cd - \
    && coverage run -a -m bugbane fuzz -vv suite ${FUZZ}/go-fuzz \
    && coverage run -a -m bugbane coverage -vv suite ${FUZZ}/go-fuzz \
    && coverage run -a -m bugbane reproduce -vv suite ${FUZZ}/go-fuzz \
    && coverage run -a -m bugbane report -vv --html-screener selenium \
        --name report_gofuzz suite ${FUZZ}/go-fuzz \
    && rm -rf /storage/go-fuzz \
    && coverage run -a -m bugbane corpus -vv suite ${FUZZ}/go-fuzz export-to /storage/go-fuzz \
    && cd ${FUZZ}/go-fuzz \
    && cp -t /storage/go-fuzz -r \
        *.md coverage_report \
        screens screenshots \
        *.json *.log \
        bug_samples dictionaries \
        2>/dev/null || : \
    && cd - \
    && : calculate SLOC and COVERAGE : \
    && cloc /bugbane/bugbane \
    && echo "INTEGRATION COVERAGE:" \
    && coverage report --include "*/bugbane/*" \
    && coverage run -a -m pytest -q \
    && echo "UNIT + INTEGRATION COVERAGE:" \
    && coverage report --include "*/bugbane/*" \
    && :
