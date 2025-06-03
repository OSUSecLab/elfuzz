with open('CXXFLAGS') as f:
    text = f.read().replace('-stdlib=libc++', '')
with open('CXXFLAGS', 'w') as f:
    f.write(text)

with open('/src/librsvg/fuzz/Cargo.toml', 'r') as f:
    lines = f.readlines()
    new_lines = []
    for line in lines:
        l = line.strip()
        if l == '[package.metadata]' or l == 'cargo-fuzz = true' or l == 'libfuzzer-sys = "0.4"':
            continue
        elif l == '[dependencies]':
            new_lines.append(l)
            new_lines.append('afl = "0.15.8"')
            continue
        new_lines.append(l)
with open('/src/librsvg/fuzz/Cargo.toml', 'w') as f:
    f.write('\n'.join(new_lines))
