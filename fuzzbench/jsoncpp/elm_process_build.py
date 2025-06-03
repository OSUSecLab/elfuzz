with open('./build.sh') as f:
    build_text = f.read().replace('$LIB_FUZZING_ENGINE', '')
with open('./build.sh', 'w') as f:
    f.write(build_text)

with open('./CXXFLAGS') as f:
    cxxflags = f.read()
    cxxflags = cxxflags.replace('-stdlib=libc++', '')
with open('./CXXFLAGS', 'w') as f:
    f.write(cxxflags)
