#!/usr/bin/env python3

import click as clk
import os
import os.path
import logging
import json
import shutil
import tempfile
import subprocess
import sys

logger = logging.getLogger(__file__)

GRMR_GRAMMAR = {
    'jsoncpp': ('json', ''),
    'ninja': ('ninja', ''),
    'php': ('php', ''),
    'cpython3': ('python3', '_patched'),
    're2': ('re2', ''),
    'cvc5': ('smtlib2', ''),
    'sqlite3': ('sqlite', ''),
    'systemd': ('systemd-networkd', ''),
    'libxml2': ('xml', ''),
    'librsvg': ('xml', '')
}

ISLA_GRAMMAR = {
    'jsoncpp': ('json', ''),
    'ninja': ('ninja', ''),
    'php': ('php', '_patched'),
    'cpython3': ('python3', '_patched'),
    're2': ('re2', ''),
    'cvc5': ('smtlib2', ''),
    'sqlite3': ('sqlite', ''),
    'systemd': ('systemd-networkd', ''),
    'libxml2': ('xml', ''),
    'librsvg': ('xml', ''),
}

@clk.command()
@clk.option('--force', '-f', is_flag=True, help='Force overwrite')
@clk.argument('target', type=clk.Choice([
    'cpython3',
    'cvc5',
    're2',
    'jsoncpp',
    'libxml2',
    'sqlite3',
    'librsvg',
]))
@clk.option('--fuzzer', '-z', default='elm', required=False, type=clk.Choice([
    'elm',
    'grmr',
    'isla',
    'islearn',
    'elmalt',
    'elmnoinf',
    'elmnocomp',
    'elmnospl',
]))
def main(force, target, fuzzer):
    work_root = os.path.abspath(os.path.dirname(__file__))

    match fuzzer:
        case 'elm':
            subdir = os.path.join(work_root, target)
        case 'grmr':
            subdir = os.path.join(work_root, f'{target}_grammarinator')
        case 'isla':
            subdir = os.path.join(work_root, f'{target}_isla')
        case 'islearn':
            subdir = os.path.join(work_root, f'{target}_islearn')
        case 'elmalt':
            subdir = os.path.join(work_root, f'{target}_alt')
        case 'elmnoinf':
            subdir = os.path.join(work_root, f'{target}_noinf')
        case 'elmnocomp':
            subdir = os.path.join(work_root, f'{target}_nocomp')
        case 'elmnospl':
            subdir = os.path.join(work_root, f'{target}_nospl')
        case _:
            logger.error(f'Unknown fuzzer: {fuzzer}')
            sys.exit(1)

    if os.path.exists(subdir):
        if force:
            logger.warning(f'Removing existing {subdir}')
            shutil.rmtree(subdir, ignore_errors=True)
        else:
            logger.error(f'{subdir} already exists')
            sys.exit(2)
    
    os.makedirs(subdir)
    
    
    eval_root = os.path.abspath(os.path.join(work_root, '..'))
    
    islearn_dir = os.path.join(eval_root, 'islearn_adapt', 'selected')
    islearn_files = os.listdir(islearn_dir)
    islearn_store = {}
    for fn in islearn_files:
        if not fn.endswith('.isla'):
            continue
        else:
            head, _ = fn.split('_')
            assert head not in islearn_store
            islearn_store[head] = os.path.join(islearn_dir, fn)
    
    
    bin_dir = os.path.join(eval_root, 'binary', target)
    with open(os.path.join(bin_dir, 'meta.json'), 'r') as f:
        binary_metainfo = json.load(f)
    shutil.copy(os.path.join(bin_dir, binary_metainfo['binary']), subdir)
    
    support_files = binary_metainfo['support']
    for support_file1 in support_files:
        support_file = os.path.join(bin_dir, support_file1)
        if support_file.endswith('.tar.xz'):
            shutil.unpack_archive(support_file, subdir, 'xztar')
        else:
            shutil.copy(support_file, subdir)
    match fuzzer:
        case 'elm':
            fuzz_driver_dir = os.path.join(eval_root, 'fuzzdrivers', 'elmfuzz')
        case 'grmr':
            fuzz_driver_dir = os.path.join(eval_root, 'fuzzdrivers', 'grammarinator')
        case 'isla':
            fuzz_driver_dir = os.path.join(eval_root, 'fuzzdrivers', 'isla')
        case 'islearn':
            fuzz_driver_dir = os.path.join(eval_root, 'fuzzdrivers', 'isla')
        case 'elmalt' | 'elmnoinf' | 'elmnocomp' | 'elmnospl':
            fuzz_driver_dir = os.path.join(eval_root, 'fuzzdrivers', 'elmfuzz')
        case _:
            return NotImplemented()
    shutil.copy(os.path.join(fuzz_driver_dir, 'driver.py'), subdir)
    shutil.copy(os.path.join(fuzz_driver_dir, 'cov_scripts', f'{target}.py'), os.path.join(subdir, 'get_cov.py'))
    extra_scripts_dir = os.path.join(fuzz_driver_dir, 'extra', target)
    if os.path.exists(extra_scripts_dir):
        for f in os.listdir(extra_scripts_dir):
            shutil.copy(os.path.join(extra_scripts_dir, f), subdir)

    match fuzzer:
        case 'elm' | 'elmalt' | 'elmnoinf' | 'elmnocomp' | 'elmnospl':
            match fuzzer:
                case 'elm':
                    elm_fuzzer_dir = os.path.join(eval_root, 'elmfuzzers')
                case 'elmalt':
                    elm_fuzzer_dir = os.path.join(eval_root, 'alt_elmfuzzers')
                case 'elmnoinf':
                    elm_fuzzer_dir = os.path.join(eval_root, 'noinf_fuzzers')
                case 'elmnocomp':
                    elm_fuzzer_dir = os.path.join(eval_root, 'nocomp_fuzzers')
                case 'elmnospl':
                    elm_fuzzer_dir = os.path.join(eval_root, 'nospl_fuzzers')
            
            elm_fuzzers = None
            for fn in os.listdir(elm_fuzzer_dir):
                if fn.startswith(target) and fn.endswith('.tar.xz'):
                    elm_fuzzers = os.path.join(elm_fuzzer_dir, fn)
                    break
            assert elm_fuzzers is not None, f'No ELM fuzzer found for {target}'
            top_level = os.path.basename(elm_fuzzers).removesuffix(".tar.xz")
                
            with tempfile.TemporaryDirectory() as td:
                shutil.unpack_archive(elm_fuzzers, td, 'xztar')
                for fn in os.listdir(os.path.join(td, top_level)):
                    if not fn.endswith('.py'):
                        logger.warning(f'Skipping {fn}')
                        continue
                    tmp = fn[:-3]
                    canonical_name = tmp.replace('-', '_').replace('.', '_') + '.py'
                    shutil.move(os.path.join(td, top_level, fn), os.path.join(subdir, canonical_name))

        case 'grmr':
            grammar_dir, suffix = GRMR_GRAMMAR[target]
            grammar_dir = os.path.join(eval_root, 'grammars', grammar_dir, f'antlr{suffix}')
            files = os.listdir(grammar_dir)
            g4_files = [f for f in files if f.endswith('.g4')]
            if len(g4_files) == 1:
                grammar_files = g4_files
            elif len(g4_files) == 2:
                lex_file = [f for f in g4_files if f.endswith('Lexer.g4')][0]
                parser_file = [f for f in g4_files if f.endswith('Parser.g4')][0]
                grammar_files = [lex_file, parser_file]
            else:
                logger.error(f'Wrong number of grammar files for {target}')
                return
            cmd = ['grammarinator-process', '-o', subdir] + [os.path.join(grammar_dir, f) for f in grammar_files]
            logger.info(f'Running: {" ".join(cmd)}')
            subprocess.run(cmd, check=True, stderr=sys.stderr, stdout=sys.stdout)
        case 'isla':
            grammar_dir, suffix = ISLA_GRAMMAR[target]
            grammar_dir = os.path.join(eval_root, 'grammars', grammar_dir, f'isla{suffix}')
            files = os.listdir(grammar_dir)
            bnf_files = [f for f in files if f.endswith('.bnf')]
            assert len(bnf_files) == 1, f'Wrong number of grammar files for {target}'
            grammar_file = bnf_files[0]
            shutil.copy(os.path.join(grammar_dir, grammar_file), subdir)
        case 'islearn':
            grammar_dir, suffix = ISLA_GRAMMAR[target]
            grammar_dir = os.path.join(eval_root, 'grammars', grammar_dir, f'isla{suffix}')
            files = os.listdir(grammar_dir)
            bnf_files = [f for f in files if f.endswith('.bnf')]
            assert len(bnf_files) == 1, f'Wrong number of grammar files for {target}'
            grammar_file = bnf_files[0]
            shutil.copy(os.path.join(grammar_dir, grammar_file), subdir)
            shutil.copy(islearn_store[target], os.path.join(subdir, 'seman.isla'))
        case _:
            return NotImplemented()

if __name__ == '__main__':
    main()
