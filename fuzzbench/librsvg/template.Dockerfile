FROM ghcr.io/cychen2021/placeholder

#$include_dockerfile$

RUN apt-get update
RUN echo $CXXFLAGS >> $SRC/CXXFLAGS
RUN rustup install 1.79.0
RUN rustup default 1.79.0
RUN cargo install cargo-afl@0.15.8 --locked


RUN cd "$SRC/librsvg" && git pull --unshallow && git checkout e32687a7f960a99672635758812b8e7e8e184933 && cd "$SRC"
COPY elmbuild.sh $SRC
COPY Cargo.lock $SRC/$__PROJECT_DIR/fuzz/Cargo.lock
RUN chmod 777 $SRC/elmbuild.sh
COPY elm_process_build.py $SRC
RUN cd $SRC && python3 elm_process_build.py
COPY elm_main.rs $SRC/elm_main.rs

#$ON_GLADE$ ENV GLADE_MODE=true
COPY elm_prepare_entry_file.py $SRC/elm_prepare_entry_file.py
RUN cd $SRC && python3 $SRC/elm_prepare_entry_file.py "$__ENTRY_FILE"

WORKDIR $SRC/$__PROJECT_DIR
#RUN apt-get -y install libglib2.0-dev libcairo2-dev libpango1.0-dev

RUN pip install meson==1.6.1

RUN ../elmbuild.sh

# RUN python3 -m ensurepip --upgrade
RUN pip3 install click tqdm

COPY elm_getcov_inside_docker.py $SRC/elm_getcov_inside_docker.py