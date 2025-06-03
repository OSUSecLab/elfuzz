with open('./build.sh') as f:
    build_text = f.read().replace('make -j $(nproc)', 'bazel build fuzzer').replace(
'''$CXX $CXXFLAGS $SRC/target.cc -I . obj/libre2.a -lpthread $FUZZER_LIB \\
    -o $OUT/fuzzer''', ''
    )
with open('./build.sh', 'w') as f:
    f.write(build_text)

with open('re2/BUILD.bazel') as f:
    build_lines = list(
        map(lambda l: l if not l.endswith('\n') else l[:-1], f.readlines())
    )

build_lines = [
    'cc_binary(',
    '    name = "fuzzer",',
    '    srcs = ["target.cc"],',
    '    deps = [',
    '        "re2",',
    '    ],',
    ')'
] + build_lines

with open('re2/BUILD.bazel', 'w') as f:
    f.write('\n'.join(build_lines))
