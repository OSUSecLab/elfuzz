#$import_base$
FROM ghcr.io/cychen2021/placeholder

ENV CC=clang
ENV CXX=clang++
RUN apt-get update -y && apt-get install -y wget

ENV SRC=/src
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-py310_25.5.1-1-Linux-x86_64.sh -O install-miniconda.sh && bash install-miniconda.sh -b -p /home/appuser/miniconda3
RUN rm -rf install-miniconda.sh
ENV PATH=/home/appuser/miniconda3/bin:$PATH
RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main/
RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r/
RUN conda create -y -n py310 python=3.10
SHELL ["conda", "run", "-n", "py310", "/bin/bash", "-c"]

# Upgrade pip and install wheel within the virtual environment
RUN pip install --upgrade pip wheel
RUN pip install "click==8.1.8"
COPY tmp/isla /tmp/isla
COPY tmp/islearn /tmp/islearn
RUN pip install /tmp/isla
RUN pip install /tmp/islearn

COPY evaluation/islearn_adapt/oracles/__PROJECT_DIR/patch.py $SRC
RUN python $SRC/patch.py

#$cond_build$
COPY evaluation/islearn_adapt/oracles/__PROJECT_DIR/elmbuild.sh $SRC/elmbuild.sh

RUN bash $SRC/elmbuild.sh
COPY evaluation/islearn_adapt/oracles/__PROJECT_DIR/oracle.py $SRC
COPY evaluation/islearn_adapt/infer_semantics.py $SRC
COPY evaluation/grammars/__GRAMMAR_DIR/grammar.bnf $SRC
RUN conda init
RUN echo "conda activate py310" >> /root/.bashrc
WORKDIR $SRC

#$cond_positive$
ADD evaluation/islearn_adapt/oracles/__PROJECT_DIR/positive_seeds.tar.xz $SRC/positive_seeds

#$cond_negative$
ADD evaluation/islearn_adapt/oracles/__PROJECT_DIR/negative_seeds.tar.xz $SRC/negative_seeds

#$cond_post$
COPY evaluation/islearn_adapt/oracles/__PROJECT_DIR/postprocess.py $SRC

#$cond_post$
RUN python $SRC/postprocess.py

ENV ISLA_TARGET=__ISLA_TARGET
