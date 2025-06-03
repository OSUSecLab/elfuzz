#!/usr/bin/bash

cwd=$(pwd)
# cd "$SRC/libxml2" && git checkout 8318b5a63465f5805cf3e9ebad794f4db40b5aae && cd "$cwd"
export CXXFLAGS=$(cat "$SRC/CXXFLAGS")
bash "$SRC"/build.sh
