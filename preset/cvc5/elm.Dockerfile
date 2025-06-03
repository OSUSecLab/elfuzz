FROM ubuntu:noble

RUN mkdir /src
WORKDIR /src
RUN apt-get update && apt-get -y install build-essential git
RUN git clone -b cvc5-1.1.2 https://github.com/cvc5/cvc5.git
WORKDIR /src/cvc5
RUN apt-get install -y afl++ cmake python3-venv m4
RUN python3 -m venv /src/venv
ENV PATH=/src/venv/bin:$PATH
RUN pip install pyparsing
ENV CC=afl-cc
ENV CXX=afl-c++
RUN ./configure.sh --auto-download
RUN make -C build
RUN mkdir /out
RUN cp build/bin/cvc5 /out/cvc5
COPY elm_getcov_inside_docker.py /src/elm_getcov_inside_docker.py
RUN pip install click tqdm
