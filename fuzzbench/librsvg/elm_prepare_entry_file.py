import sys
import os

GLADE_MODE = os.getenv('GLADE_MODE', 'false').lower() == 'true'

entry_files = sys.argv[1].split(';')

for f in entry_files:
    with open(f) as entry_file:
        new_lines = []
        if GLADE_MODE:
            new_lines.append('use std::process::exit;')
        has_stdio = False
        for line in entry_file:
            l = line.strip()
            if l == '#![no_main]':
                continue
            elif l == 'use libfuzzer_sys::{fuzz_target, Corpus};':
                continue
            elif l == 'fuzz_target!(|data: &[u8]| -> Corpus {':
                new_lines.append('fn fuzz(data: &[u8]) -> bool {')
            elif l == '});':
                new_lines.append('}')
            else:
                new_lines.append(l)
    with open('./elm_main.rs') as main_f:
        main_lines = []
        in_main = False
        for line in main_f:
            l = line.strip()
            if line.startswith('//$main_begin$'):
                in_main = True
            elif line.startswith('//$main_end$'):
                in_main = False
            if in_main:
                if line[-1] == '\n':
                    line = line[:-1]
                main_lines.append(line)
    new_lines.extend(main_lines)
    if not GLADE_MODE:
        text = '\n'.join(new_lines).replace('Corpus::Keep', 'true').replace('Corpus::Reject', 'false')
    else:
        text = '\n'.join(new_lines).replace('Corpus::Keep', '{exit(0); true}').replace('Corpus::Reject', '{exit(1); false}')
    with open(f, 'w') as entry_file:
        entry_file.write(text)
