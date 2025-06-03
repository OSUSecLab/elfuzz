#!/usr/bin/env xonsh

import click as clk
import os.path

USE_CALLBACKS = [
    'cpython3',
    'jsoncpp',
    're2',
    'sqlite3'
]

GENERATORS = {
    'cpython3': 'generate_python3',
    'jsoncpp': 'generate_json',
    'cvc5': 'generate_smtlib2',
    'libxml2': 'generate_xml',
    'ninja': 'generate_ninja',
    're2': 'generate_regex',
    'systemd': 'generate_systemd_link',
    'php': 'generate_php',
    'sqlite3': 'generate_sql',
    'librsvg': 'generate_svg',
}

GRMR_GENERATOR = {
    'cpython3': 'Python3Generator.Python3Generator',
    'jsoncpp': 'JSONGenerator.JSONGenerator',
    'cvc5': 'SMTLIBv2Generator.SMTLIBv2Generator',
    'libxml2': 'XMLGenerator.XMLGenerator',
    'ninja': 'NinjaGenerator.NinjaGenerator',
    're2': 'regexGenerator.regexGenerator',
    'systemd': 'SystemdNetworkdGenerator.SystemdNetworkdGenerator',
    'php': 'PhpGenerator.PhpGenerator',
    'sqlite3': 'SQLiteGenerator.SQLiteGenerator',
    'librsvg': 'XMLGenerator.XMLGenerator',
}

@clk.command()
@clk.option('--force', '-f', is_flag=True, help='Force the execution of the command', default=False, required=False)
@clk.argument('target', required=True, type=str)
@clk.option('--num', '-n', type=int, required=False, default=-1)
@clk.option('--time-limit', '-t', type=int, required=False, default=-1, help="Time limit in seconds")
@clk.option('--batch-size', '-b', type=int, required=False, default=10000)
@clk.option('--para-num', '-j', type=int, required=False, default=60)
@clk.option('--afl-dir', '-a', type=str, required=False, default='/usr/bin')
@clk.option('--size-limit', '-s', type=int, required=False, default=2048)
@clk.option('--fuzzer', '-z', type=str, required=False, default='elm')
@clk.option('--batch-timeout', '-q', type=int, required=False, default=-1)
@clk.option('--race-mode', '-r', is_flag=True, default=False, required=False)
@clk.option('--checkpoint', '-c', default=-1, type=int, required=False)
def main(force, target, num, time_limit, batch_size, para_num, afl_dir, size_limit, 
         fuzzer, batch_timeout, race_mode, checkpoint):
    if time_limit == -1 and num == -1:
        yes = input('The time limit and num limit are both unset. Continue? [yn]')
        match yes:
            case 'y':
                pass
            case _:
                return
                
    cwd = os.path.dirname(os.path.abspath(__file__))

    options = []
    match fuzzer:
        case 'elm' | 'elmalt' | 'elmnocomp' | 'elmnospl' | 'elmnoinf' | 'zest':
            match fuzzer:
                case 'elm':
                    target_dir = os.path.join(cwd, target)
                case 'elmalt':
                    target_dir = os.path.join(cwd, f'{target}_alt')
                case 'elmnocomp':
                    target_dir = os.path.join(cwd, f'{target}_nocomp')
                case 'elmnospl':
                    target_dir = os.path.join(cwd, f'{target}_nospl')
                case 'elmnoinf':
                    target_dir = os.path.join(cwd, f'{target}_noinf')
                case 'zest':
                    target_dir = os.path.join(cwd, f'{target}_zest')
            options += [
                '-g', GENERATORS[target],
            ]
        case 'grmr':
            target_dir = os.path.join(cwd, f'{target}_grammarinator')
            options += [
                '-g', GRMR_GENERATOR[target],
            ]
        case 'isla':
            target_dir = os.path.join(cwd, f'{target}_isla')
        case 'islearn':
            target_dir = os.path.join(cwd, f'{target}_islearn')
            options += ['--use-semantics', 'true']
    if fuzzer in ['isla', 'islearn', 'elm', 'elmalt', 'elmnospl', 'elmnoinf', 'elmnocomp'] and batch_timeout != -1:
        options += ['-q', str(batch_timeout)]
    options += ['-c', str(checkpoint)]

    if force:
        options.append('-f')
    if num != -1:
        options += ['-n', str(num)]
    if time_limit != -1:        
        options += ['-t', str(time_limit)]
    options += ['-b', str(batch_size), '-j', str(para_num), '-a', afl_dir]
    if target in USE_CALLBACKS:
        options += ['-cb', 'callback']
    if fuzzer in ['elm', 'elmalt']:
        options += ['-s', str(size_limit)]
    
    options + ['--stat-file', f'{target_dir}/stat.record']
    if race_mode:
        options += ['--race-mode']

    print(f'Launch: python3 {target_dir}/driver.py -d {target_dir} {" ".join(options)}')

    python3 @(target_dir)/driver.py -d @(target_dir) @(options)

main()
