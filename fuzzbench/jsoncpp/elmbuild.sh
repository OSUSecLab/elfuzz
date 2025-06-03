#!/usr/bin/bash

# cwd=$(pwd)
# cd "$SRC/jsoncpp" && git checkout 69098a18b9af0c47549d9a271c054d13ca92b006 && cd "$cwd"

export CXXFLAGS=$(cat "$SRC/CXXFLAGS")
bash "$SRC"/build.sh
