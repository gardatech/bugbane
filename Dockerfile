# Docker image with BugBane tools

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

FROM base AS bugbane_tools

COPY . /bugbane

RUN cd /bugbane && \
    python3 -m pip install -e .[all] && \
    pytest && echo "Tests: OK"
