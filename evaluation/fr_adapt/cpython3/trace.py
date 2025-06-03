import re

def extract_def_func(line) -> str | None:
    pattern = re.compile(r'define .*\@([a-zA-Z_][a-zA-Z_0-9.]*)\(.*\) .+ !dbg !(\d+) \{\n')
    if (m := pattern.fullmatch(line)) is None:
        return None
    return m.group(1)


def build_func_map(lines: list[str]) -> dict[str, int]:
    func_map = {}
    for idx, l in enumerate(lines):
        if (func_name := extract_def_func(l)) is not None:
            func_map[func_name] = idx
    return func_map

def extract_func_body(lines: list[str], func_line: int) -> list[str]:
    result = []
    for l in range(func_line, len(lines)):
        if lines[l] == '}\n':
            result.append(lines[l])
            return result
        result.append(lines[l])

def extract_call_func(line: str) -> str | None:
    pattern = re.compile(r'(.* )?call .*@([a-zA-Z_][a-zA-Z_0-9.]*)\(.*\).*')
    if (m := pattern.fullmatch(line.strip())) is None:
        return None
    return m.group(2)


if __name__ == '__main__':
    with open('fuzzer.ll', 'r') as f:
        lines = f.readlines()
    func_map = build_func_map(lines)
    
    queue = ['main']
    result = set()
    
    counter = 0
    while queue:
        func = queue.pop(0)
        # assert func not in result, f'{func} already in result'
        if func in ['LLVMFuzzerInitialize']:
            continue
        if func in result:
            continue
        if func not in func_map:
            continue
        counter += 1
        print(f'{counter}: {func}')
        result.add(func)
        body = extract_func_body(lines, func_map[func])
        for l in body:
            if (call_func := extract_call_func(l)) is not None and call_func not in result:
                queue.append(call_func)
    print(len(result))
    # print(list(result)[:10])
    with open('funcs_use_anders.txt', 'w') as f:
        f.writelines([f'{l}\n' for l in result])
