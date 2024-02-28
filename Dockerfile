# Docker image with BugBane tools

FROM archlinux AS base
RUN : \
    && pacman --noconfirm --needed -Syu \
        vim nano tmux bash-completion python python-pip \
        base-devel git cmake gdb strace ltrace diffutils \
        clang llvm lld lib32-gcc-libs \
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

ARG GIT_ANSIFILTER_TAG="2.18"
RUN : \
    && git clone --depth=1 https://gitlab.com/saalen/ansifilter.git \
        -b "$GIT_ANSIFILTER_TAG" /ansifilter \
    && cd /ansifilter \
    && make -j \
    && make install \
    && cd / \
    && rm -rf /ansifilter \
    && :

ARG GIT_AFLPP_TAG="v4.08c"
RUN : \
    && git clone --depth 1 https://github.com/AFLplusplus/AFLplusplus \
        -b "$GIT_AFLPP_TAG" /AFLplusplus \
    && cd /AFLplusplus \
    && sed -i 's|cc_params\[cc_par_cnt++\] = "-fsanitize-undefined-trap-on-error";||g' ./src/afl-cc.c \
    && sed -i 's|"-fsanitize=cfi";|"-fsanitize=cfi";\n    cc_params\[cc_par_cnt++\] = "-fno-sanitize-trap=cfi";|g' ./src/afl-cc.c \
    && sed -i 's|#define FANCY_BOXES|// #define FANCY_BOXES|g' ./include/config.h \
    && sed -i 's|#define STATS_UPDATE_SEC .*$|#define STATS_UPDATE_SEC 5|g' ./include/config.h \
    && export NO_NYX=1 \
    && make source-only \
    && make install \
    && :


# cache BugBane deps
COPY requirements.txt requirements_dev.txt /bugbane/
ENV PIP_BREAK_SYSTEM_PACKAGES=1
ENV PIP_NO_CACHE_DIR=1
RUN pip3 install -r/bugbane/requirements{,_dev}.txt



FROM base AS bugbane_tools
COPY . /bugbane

RUN : \
    && cd /bugbane \
    && pip3 install -e .[all] \
    && pytest \
    && :
