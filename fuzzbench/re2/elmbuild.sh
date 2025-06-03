#!/usr/bin/bash

# cwd=$(pwd)
# cd "$SRC/re2" && git checkout 4a8cee3dd3c3d81b6fe8b867811e193d5819df07 && cd "$cwd"

export CXXFLAGS=$(cat "$SRC/CXXFLAGS")
bash "$SRC"/build.sh
