import re

def extract_func_name(line):
    pattern = re.compile(r'define (.* )?(%?[a-zA-Z_][_a-zA-Z0-9.]*\*?) \@([a-zA-Z_][.a-zA-Z_0-9]*)\((.*)\).*{\n')
    if (m := pattern.fullmatch(line)) is None:
        return None
    return m.group(3), f'declare {m.group(2)} @{m.group(3)}({m.group(4)})\n'

def tailor_ll(lines, funcs):
    results = []

    state = 0
    
    for idx, l in enumerate(lines):
        if state == 0:
            if (m := extract_func_name(l)) is not None and m[0] not in funcs:
                state = 1
                results.append(m[1])
            else:
                results.append(l)
        if state == 1:
            if l == '}\n':
                state = 0
    return results

if __name__ == '__main__':
    with open('funcs_use_anders.txt', 'r') as f:
        funcs = set([l.strip() for l in f.readlines()])
    with open('fuzzer.ll', 'r') as f:
        lines = f.readlines()
    tailored = tailor_ll(lines, funcs)

    with open('fuzzer_patched.ll', 'w') as f:
        f.writelines(tailored)
