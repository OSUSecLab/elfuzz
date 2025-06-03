#!/usr/bin/bash

set -o errexit                                                                                                                                                                                                                               set -o pipefail                                                                                                                                                                                                                              set -o nounset

PREFIX="/usr"

# Don't instrument the third-party dependencies that we build
CFLAGS_SAVE="$CFLAGS"
#CXXFLAGS_SAVE="$CXXFLAGS"
unset CFLAGS
unset CXXFLAGS

# Compile and install GLib
cd "$SRC/glib"
git submodule update --init --recursive
meson setup --prefix="$PREFIX" --buildtype=plain --default-library=static builddir -Dtests=false
ninja -C builddir
ninja -C builddir install

# Compile and install FreeType
cd "$SRC/freetype"
git submodule update --init --recursive
meson setup --prefix="$PREFIX" --buildtype=plain --default-library=static builddir
ninja -C builddir
ninja -C builddir install

# Compile and install Cairo
cd "$SRC/cairo"
git submodule update --init --recursive
meson setup --prefix="$PREFIX" --buildtype=plain --default-library=static builddir -Dfreetype=enabled -Dfreetype:tests=disabled -Dfreetype:tools=disabled -Dfontconfig=enabled -Dfontconfig:tests=disabled -Dfontconfig:tools=disabled -Dpixman:tests=disabled -Dtests=disabled
ninja -C builddir
ninja -C builddir install

# Compile and install HarfBuzz
cd "$SRC/harfbuzz"
git submodule update --init --recursive
meson setup --prefix="$PREFIX" --buildtype=plain --default-library=static builddir -Dtests=disabled
ninja -C builddir
ninja -C builddir install

# Compile and install Pango
cd "$SRC/pango"
git submodule update --init --recursive
meson setup --prefix="$PREFIX" --buildtype=plain --default-library=static builddir
ninja -C builddir
ninja -C builddir install

# Restore the compiler flag environment variables
export CFLAGS="${CFLAGS_SAVE}"
#export CXXFLAGS="${CXXFLAGS_SAVE}"
export CXXFLAGS=$(cat "$SRC/CXXFLAGS")
cd "$SRC"/librsvg/fuzz/ 
cargo afl build --bin render_document
cp "$SRC"/librsvg/fuzz/target/debug/render_document "$OUT"/

