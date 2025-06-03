#!/usr/bin/bash

export CXXFLAGS=$(cat "$SRC/CXXFLAGS")
bash "$SRC"/build.sh
