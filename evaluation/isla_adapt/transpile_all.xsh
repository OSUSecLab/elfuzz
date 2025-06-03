#!/usr/bin/env xonsh

import os

grammar_dirs = os.listdir('../grammars')

for grammar_dir in grammar_dirs:
    print(f'Transpiling {grammar_dir}')
    if not os.path.isdir(f'../grammars/{grammar_dir}'):
        continue
    if not os.path.exists(f'../grammars/{grammar_dir}/isla'):
        os.mkdir(f'../grammars/{grammar_dir}/isla')

    if os.path.exists(f'../grammars/{grammar_dir}/antlr_patched'):
        antlr4_dir = 'antlr_patched'
        grammar_files = os.listdir(f'../grammars/{grammar_dir}/antlr_patched')
    else:
        antlr4_dir = 'antlr'
        grammar_files = os.listdir(f'../grammars/{grammar_dir}/antlr')
    g4_files = []
    props = {}
    for file in grammar_files:
        if file.endswith('.g4'):
            g4_files.append(f'../grammars/{grammar_dir}/{antlr4_dir}/{file}')
        elif file == 'prop':
            with open(f'../grammars/{grammar_dir}/{antlr4_dir}/{file}') as f:
                for line in f:
                    key, value = line.split('=')
                    props[key.strip()] = value.strip()
        else:
            continue
    extra_options = []
    if 'whitespace' in props:
        extra_options.append(f'-ws')
        extra_options.append(props["whitespace"])
    python transpile_g4.py --log-level INFO -o @(f'../grammars/{grammar_dir}/isla/grammar.bnf') @(extra_options) @(g4_files)
