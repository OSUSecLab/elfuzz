# Use Ubuntu 24.04 as the base image
FROM ubuntu:24.04 AS dev

ARG USER_ID=1000

# Avoid warnings by switching to noninteractive
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y apt-utils

# RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test
# RUN apt-get update
RUN apt-get update && apt-get install -y \
    software-properties-common \
    build-essential \
    libssl-dev \
    libffi-dev \
    gpg-agent \
    build-essential \
    git \
    openssh-server \
    rsync \
    qtbase5-dev \
    qt5-qmake \
    cmake \
    vim \
    curl \
    git-lfs \
    llvm-dev \
    gcc-13-plugin-dev \
    clang \
    cvc5 \
    sudo && \
    rm -rf /var/lib/apt/lists/*
RUN sudo apt-get install -y --only-upgrade libstdc++6

RUN echo root:root | chpasswd

RUN userdel -r $(id -nu $USER_ID 2>/dev/null) || true

# Create a non-root user
RUN useradd --create-home appuser --uid $USER_ID && \
    echo appuser:appuser | chpasswd && \
    echo 'appuser ALL=(root) NOPASSWD: ALL' >> /etc/sudoers
RUN chsh appuser -s /usr/bin/bash
USER appuser
WORKDIR /home/appuser
RUN case $(uname -m) in \
    aarch64) wget https://repo.anaconda.com/miniconda/Miniconda3-py312_25.3.1-1-Linux-aarch64.sh -O install-miniconda.sh && bash install-miniconda.sh -b -p /home/appuser/miniconda3;; \
    x86_64) wget https://repo.anaconda.com/miniconda/Miniconda3-py312_25.3.1-1-Linux-x86_64.sh -O install-miniconda.sh && bash install-miniconda.sh -b -p /home/appuser/miniconda3;; \
    *) echo "Unsupported architecture" && exit 1;; \
    esac
RUN rm -rf install-miniconda.sh
ENV PATH=/home/appuser/miniconda3/bin:$PATH
RUN conda create -y -n py310 python=3.10
SHELL ["conda", "run", "-n", "py310", "/bin/bash", "-c"]

# Upgrade pip and install wheel within the virtual environment
RUN pip install --upgrade "pip==25.1.1" "wheel==0.45.1"
RUN pip install "ruamel.yaml==0.17.21" "requests==2.32.3" "tqdm==4.67.1" "plotext==5.3.2"

RUN git clone https://github.com/google/fuzzbench.git
RUN cd fuzzbench && git checkout 6228338e8cfb654bb44b71402e05860a93d60ab1

# I don't know why but the install-dependencies fails on aarch64
RUN if [ $(uname -m) != "aarch64" ]; then make install-dependencies -C fuzzbench; fi

RUN curl -fsSL https://get.docker.com | sudo sh -s -- --version 28.2.2

# The ID of the docker group should be set the same as the host machine at runtime
RUN sudo groupdel docker 

RUN sudo apt-get install -y afl++
WORKDIR /home/appuser
RUN python3 -m pip install "pipx==1.7.1"
RUN python3 -m pipx ensurepath

ADD tmp/elfuzz_baselines.tar.zst /tmp/
RUN pipx install /tmp/isla

RUN if [ $(uname -m) != "aarch64" ]; then pipx install "xonsh==0.19.3" "grammarinator==23.7"; else pipx install "xonsh==0.19.3" "grammarinator==23.7"; fi
RUN pipx inject xonsh "click==8.1.8"

# It seems that the isla-solver is not compilable on aarch64
RUN if [ $(uname -m) != "aarch64" ]; then pipx inject isla-solver setuptools; fi
ENV PATH=/home/appuser/elmfuzz/cli:/home/appuser/.local/bin:$PATH
RUN pip install "python-lsp-server[all]==1.12.2" "click==8.1.8" "numpy==1.26.4" "requests==2.32.4"
RUN case $(uname -m) in \
    aarch64) sudo curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-aarch64 -o /usr/local/bin/docker-compose;; \
    x86_64) sudo curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose;; \
    *) echo "Unsupported architecture" && exit 1;; \
    esac
RUN sudo chmod 777 /usr/local/bin/docker-compose
RUN pip install "yamlpath==3.8.2" "ast-comments==1.2.2"
WORKDIR /home/appuser
RUN git clone https://github.com/google/oss-fuzz.git
RUN cd oss-fuzz && git checkout f06c2b532c232b4bfff6ba24720ca15fac6078b4
RUN pip install "antlr4-tools==0.2.2" "antlr4-python3-runtime==4.13.2" "networkx==3.4.2" "parsy==2.1"
RUN curl --proto '=https' --tlsv1.2 https://sh.rustup.rs -sSf | bash -s -- -y
RUN /home/appuser/.cargo/bin/cargo install cargo-afl@0.15.10
RUN conda init
RUN conda config --set changeps1 false
RUN echo "conda activate py310" >> /home/appuser/.bashrc
RUN echo "conda config --set changeps1 false" >> /home/appuser/.bash_profile
ENV LD_LIBRARY_PATH=/home/appuser/miniconda3/envs/py310/lib:$LD_LIBRARY_PATH
# RUN pip install https://github.com/cychen2021/isla/archive/refs/tags/240804.zip
RUN sudo update-alternatives --install /home/appuser/miniconda3/envs/py310/lib/libtinfo.so.6.4 libtinfo64 /usr/lib/$(uname -m)-linux-gnu/libtinfo.so.6.4 100
RUN sudo update-alternatives --install /home/appuser/miniconda3/envs/py310/lib/libtinfo.so.6 libtinfo6 /usr/lib/$(uname -m)-linux-gnu/libtinfo.so.6.4 100
RUN sudo update-alternatives --install /home/appuser/miniconda3/envs/py310/lib/libtinfo.so libtinfo /usr/lib/$(uname -m)-linux-gnu/libtinfo.so.6.4 100
RUN sudo update-alternatives --install /home/appuser/miniconda3/envs/py310/lib/libstdc++.so.6 libstdc++ /usr/lib/$(uname -m)-linux-gnu/libstdc++.so.6 100
RUN sudo update-alternatives --install /usr/bin/cc cc /usr/bin/$(uname -m)-linux-gnu-gcc-13 99
RUN sudo update-alternatives --install /usr/bin/c++ c++ /usr/bin/$(uname -m)-linux-gnu-g++-13 99
RUN sudo apt-get install -y zlib1g-dev pkg-config meson unzip zip zstd
RUN sudo apt-get install -y jq bc
RUN pip install https://github.com/cychen2021/idontwannadoresearch/archive/refs/tags/v0.0.58.zip
RUN pip install "colorama==0.4.6" "bc==0.0.1" "toml==0.10.2" "ruamel.yaml==0.18.14" "pexpect==4.9.0"
# RUN sudo apt-get install -y postgresql-common
# RUN sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
# RUN sudo apt-get update -y && sudo apt-get install -y postgresql-16
ENV FIXREVERTER=off

FROM dev AS publish

COPY . /home/appuser/elmfuzz
RUN sudo chown -R appuser:appuser /home/appuser/elmfuzz

WORKDIR /home/appuser/elmfuzz
RUN git submodule init
RUN git submodule update --init --recursive

RUN sudo mkdir -p /elfuzz && sudo chown -R appuser:appuser /elfuzz
RUN sudo ln -s /home/appuser/elmfuzz/docs /elfuzz/docs
RUN sudo ln -s /home/appuser/elmfuzz/cli/elfuzz /elfuzz/elfuzz
RUN sudo ln -s /home/appuser/elmfuzz/docker_readme.md /elfuzz/README.md
RUN mkdir /elfuzz/plot
RUN sudo ln -s /home/appuser/elmfuzz/plot/fig /elfuzz/plot/figure
RUN sudo ln -s /home/appuser/elmfuzz/plot/table /elfuzz/plot/table
RUN sudo ln -s /home/appuser/elmfuzz/analysis /elfuzz/analysis
RUN sudo update-alternatives --install /usr/bin/python3 python3 /home/appuser/miniconda3/envs/py310/bin/python3 100
RUN sudo update-alternatives --install /usr/bin/python python /home/appuser/miniconda3/envs/py310/bin/python 100

RUN bash .devcontainer/install-sdkman.sh
RUN source "$HOME/.sdkman/bin/sdkman-init.sh" && sdk install java 8.0.452-amzn

WORKDIR /elfuzz
RUN mv /tmp/glade /home/appuser/glade
RUN mv /tmp/isla /home/appuser/elmfuzz/tmp/isla
RUN mv /tmp/islearn /home/appuser/elmfuzz/tmp/islearn

ENV ELFUZZ_PROJECT_ROOT=/home/appuser/elmfuzz
ENV ENTRY_ROOT=/elfuzz
ENV PATH=/home/appuser/.local/bin:$PATH
RUN pipx install "pyexcel-cli==0.0.3"
RUN pipx inject pyexcel-cli "pyexcel-xlsx==0.6.1"
RUN pip install "pandas==2.3.0" "openpyxl==3.1.5" "xlsxwriter==3.2.5" "matplotlib==3.10.3"

# Sometime running AFL++ in Docker may cause problems without the following environment variable.
# This variable forces AFL++ to ignore missing crash files. Which could affect the replication of
# the results in the paper, as they didn't encounter this problem.
# However, not Docker on every machines has this problem. My PC does, but our server does not.
# So, without such a problem, the environment variable will take no effect.
ENV AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1

ENTRYPOINT ["/usr/bin/bash"]
