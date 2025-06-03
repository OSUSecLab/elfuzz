#!/usr/bin/env bash

export CC="/src/aflplusplus/afl-gcc"
export CXX="/src/aflplusplus/afl-g++"
export CFLAGS="-static -O1 -fno-omit-frame-pointer -g -Wno-error=int-conversion -Wno-error=deprecated-declarations -Wno-error=implicit-function-declaration -Wno-error=implicit-int -DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION -DFRCOV=1"
export CXXFLAGS="$CXXFLAGS -DFRCOV=1 -static"
# export LDFLAGS="$LDFLAGS"
apt update && apt install vim -y
git stash
make distclean
git apply /tmp/tmp/fr_injection_patched.patch
patch ../elmbuild.sh /tmp/tmp/fr_injection_elmbuild_sh.diff
# patch Modules/Setup /tmp/tmp/fr_injection_setup.diff
rm -rf /out/*
