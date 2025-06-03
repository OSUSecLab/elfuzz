#!/usr/bin/bash

./configure --prefix=$OUT --disable-test-modules
export AFL_IGNORE_PROBLEMS=1
make -j$(nproc) altinstall
$CC $CFLAGS $($OUT/bin/python*-config --cflags) -I./Include/internal  -D _Py_FUZZ_ONE -D _Py_FUZZ_fuzz_pycompile -o $OUT/fuzzer Modules/_xxtestfuzz/fuzzer.c $($OUT/bin/python*-config --ldflags --embed)
