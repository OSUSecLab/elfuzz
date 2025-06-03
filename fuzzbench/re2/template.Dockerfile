FROM ghcr.io/cychen2021/placeholder

#$include_dockerfile$

ENV CC=$SRC/aflplusplus/afl-cc
ENV CXX=$SRC/aflplusplus/afl-c++
RUN echo $CXXFLAGS >> $SRC/CXXFLAGS
RUN cd "$SRC/re2" && git checkout 4a8cee3dd3c3d81b6fe8b867811e193d5819df07
RUN cp $SRC/target.cc $SRC/$__PROJECT_DIR/target.cc

COPY elmbuild.sh $SRC
RUN chmod 777 $SRC/elmbuild.sh
COPY elm_process_build.py $SRC
RUN cd $SRC && python3 elm_process_build.py
COPY elm_main.cc $SRC/elm_main.cc
COPY elm_prepare_entry_file.py $SRC/elm_prepare_entry_file.py
RUN cd $SRC && python3 $SRC/elm_prepare_entry_file.py "$__ENTRY_FILE"

WORKDIR $SRC
RUN ./elmbuild.sh

# RUN python3 -m ensurepip --upgrade
RUN pip3 install click tqdm

COPY elm_getcov_inside_docker.py $SRC/elm_getcov_inside_docker.py
RUN cp $SRC/$__PROJECT_DIR/bazel-bin/fuzzer $OUT/fuzzer
