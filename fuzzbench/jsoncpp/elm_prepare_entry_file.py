
import sys

entry_files = sys.argv[1].split(';')

for f in entry_files:
    with open(f) as entry_file:
        new_lines = []
        has_stdio = False
        for line in entry_file:
            l = line.strip()
            if l.startswith('#include <stdio.h>'):
                has_stdio = True
            new_lines.append(line)
        if not has_stdio:
            new_lines.insert(0, '#include <stdio.h>')
    with open('./elm_main.cc') as main_f:
        main_lines = []
        in_main = False
        for line in main_f:
            if line.startswith('//$main_begin$'):
                in_main = True
            elif line.startswith('//$main_end$'):
                in_main = False
            if in_main:
                if line[-1] == '\n':
                    line = line[:-1]
                main_lines.append(line)
    new_lines.extend(main_lines)
    with open(f, 'w') as entry_file:
        entry_file.write('\n'.join(new_lines))
