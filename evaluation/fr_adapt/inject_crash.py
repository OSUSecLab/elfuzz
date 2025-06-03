import re
import sys

chunks: list[tuple[int, int, list[str]]] = []

with open(sys.argv[1], 'r') as file:
    lines = file.readlines()

if len(sys.argv) >= 4 and sys.argv[3] == 'sqlite3':
    sqlite3_mode = True
else:
    sqlite3_mode = False

if sqlite3_mode:
    for idx, line in enumerate(lines):
        pattern = re.compile(r'> *fprintf\(stderr, "triggered bug index \d+\\n"\);\n')
        if pattern.fullmatch(line) is not None:
            print(f'Found trigger at {idx}')
            lines[idx] = f'> {{ {line.removeprefix(">").strip()} abort(); }}\n'
    with open(sys.argv[2], 'w') as file:
        file.writelines(lines)
    sys.exit(0)

status = 0
start_line = 0

for idx, line in enumerate(lines):
    match status:
        case 0:
            if line.startswith('@@'):
                status = 1
                start_line = idx
        case 1:
            if line.startswith('@@'):
                chunks.append((start_line, idx, lines[start_line:idx]))
                start_line = idx
            elif line.startswith('diff') or line.startswith('index') or line.startswith('---') or line.startswith('+++'):
                chunks.append((start_line, idx, lines[start_line:idx]))
                status = 0
            else:
                pass

lines_with_index = list(enumerate(lines))

def find_line_with_index(index: int, lines_with_index: list[tuple[int, str]]) -> tuple[int, str]:
    for real_index, (idx, line) in enumerate(lines_with_index):
        if idx == index:
            return real_index, line
    return -1, ''

for start_index, end_index, chunk in chunks:
    print(f'Processing chunk {start_index} to {end_index}')
    real_start_index, first_line = find_line_with_index(start_index, lines_with_index)
    pattern = re.compile(r'@@ -\d+,\d+ \+(\d+),(\d+) @@')
    heading_match = pattern.match(first_line)
    assert heading_match is not None
    start_record = int(heading_match.group(1))
    length = int(heading_match.group(2))
    print(f'Length: {length}')
    
    found = False
    trigger_match = re.compile(r'\+ *fprintf\(stderr, "triggered bug index \d+\\n"\);\n')
    original_length = end_index - start_index + 1
    for idx in range(real_start_index, real_start_index + original_length):
        line = lines_with_index[idx][1]
        if trigger_match.match(line):
            print(f'Found trigger at {idx}')
            assert idx - 1 >= real_start_index
            assert idx + 1 <= real_start_index + original_length
            lines_with_index.insert(idx, (-1, '+ {\n'))
            lines_with_index.insert(idx + 2, (-1, '+ abort();\n'))
            lines_with_index.insert(idx + 3, (-1, '+ }\n'))
            found = True
            break
    if found:
        lines_with_index[real_start_index] = (start_index, first_line.replace(f'+{start_record},{length}', f'+{start_record},{length + 3}'))
    

with open(sys.argv[2], 'w') as file:
    file.writelines([line for idx, line in lines_with_index])
    