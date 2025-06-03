FROM ghcr.io/cychen2021/placeholder

#$include_dockerfile$

RUN cd "$SRC/jsoncpp" && git checkout 69098a18b9af0c47549d9a271c054d13ca92b006 && cd $SRC

#$ON_GLADE:INSERT$
#$ON_GLADE$ RUN $SRC/glade_patch.sh

ENV CC=$SRC/aflplusplus/afl-cc
ENV CXX=$SRC/aflplusplus/afl-c++
RUN echo $CXXFLAGS >> $SRC/CXXFLAGS

COPY elmbuild.sh $SRC
RUN chmod 777 $SRC/elmbuild.sh
COPY elm_process_build.py $SRC
RUN cd $SRC && python3 elm_process_build.py
COPY elm_main.cc $SRC/elm_main.cc
COPY elm_prepare_entry_file.py $SRC/elm_prepare_entry_file.py
RUN cd $SRC && python3 $SRC/elm_prepare_entry_file.py "$__ENTRY_FILE"

WORKDIR $SRC/$__PROJECT_DIR
RUN ../elmbuild.sh

# RUN python3 -m ensurepip --upgrade
RUN pip3 install click tqdm

COPY elm_getcov_inside_docker.py $SRC/elm_getcov_inside_docker.py