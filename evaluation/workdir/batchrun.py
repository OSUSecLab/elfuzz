from pip._vendor import tomli as tomllib
import click as clk
import logging
import os
import os.path

logger = logging.getLogger(__file__)

PRESETS = {
    'isla': {
        'cpython3': ['-b', '10', '-q', '500'],
        'sqlite3': ['-b', '1', '-q', '500'],
        'jsoncpp': ['-b', '200', '-q', '500'],
        'libxml2': ['-b', '200', '-q', '500'],
        're2': ['-b', '200', '-q', '500'],
        'librsvg': ['-b', '200', '-q', '500'],
        'cvc5': ['-b', '200', '-q', '500'],
    },
    'grmr' : {
        'cpython3': [],
        'cvc5': ['-b', '1000'],
        'librsvg': ['-b', '1000'],
        'sqlite3': [],
        'jsoncpp': [],
        'libxml2': [],
        're2': [],
    },
    'islearn': {
        'libxml2': ['-b', '10', '-q', '500'],
        'cvc5': ['-b', '10', '-q', '500'],
        'librsvg': ['-b', '10', '-q', '500'],
        'sqlite3': ['-b', '20', '-q', '500'],
        'cpython3': ['-b', '10', '-q', '500'],
    },
    'elm': {
        'cpython3': [],
        'cvc5': ['-b', '1000'],
        'librsvg': ['-b', '1000'],
        'sqlite3': [],
        'jsoncpp': [],
        'libxml2': [],
        're2': [],
    },

    'elmalt': {
        'cpython3': ['-q', '30'],
        'cvc5': ['-b', '1000', '-q', '30'],
        'librsvg': ['-b', '1000', '-q', '30'],
        'sqlite3': ['-q', '30'],
        'jsoncpp': ['-q', '30'],
        'libxml2': ['-q', '30'],
        're2': ['-q', '30'],
    },
    'elmnospl': {
        'cpython3': ['-q', '30'],
        'cvc5': ['-b', '1000', '-q', '30'],
        'librsvg': ['-b', '1000', '-q', '30'],
        'sqlite3': ['-q', '30'],
        'jsoncpp': ['-q', '30'],
        'libxml2': ['-q', '30'],
        're2': ['-q', '30'],
    },
    'elmnocomp': {
        'cpython3': ['-q', '30'],
        'cvc5': ['-b', '1000', '-q', '30'],
        'librsvg': ['-b', '1000', '-q', '30'],
        'sqlite3': ['-q', '30'],
        'jsoncpp': ['-q', '30'],
        'libxml2': ['-q', '30'],
        're2': ['-q', '30'],
    },
    'elmnoinf': {
        'cpython3': ['-q', '30'],
        'cvc5': ['-b', '1000', '-q', '30'],
        'librsvg': ['-b', '1000', '-q', '30'],
        'sqlite3': ['-q', '30'],
        'jsoncpp': ['-q', '30'],
        'libxml2': ['-q', '30'],
        're2': ['-q', '30'],
    }
}

DIR_SUFFIX = {
    'elm': '',
    'grmr': '_grammarinator',
    'isla': '_isla',
    'islearn': '_islearn',
    'elmalt': '_alt',
    'elmnospl': '_nospl',
    'elmnocomp': '_nocomp',
    'elmnoinf': '_noinf',
}

TIME_LIMIT = '600'
CHECKPOINT = '60'

CWD = os.path.dirname(__file__)

import subprocess
import sys
from datetime import datetime

from idontwannadoresearch import MailLogger, watch

mailogger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml")

@clk.command()
@clk.argument('config_file', type=clk.File('rb'))
@clk.option('--log-level', '-l', type=clk.Choice(['DEBUG', 'INFO']), default='INFO')
@watch(mailogger, report_ok=True)
def main(config_file, log_level):
    if "TIME_LIMIT" in os.environ:
        global TIME_LIMIT, CHECKPOINT
        TIME_LIMIT = os.environ["TIME_LIMIT"]
        CHECKPOINT = str(int(TIME_LIMIT) // 10)
    match log_level:
        case 'INFO':
            logging.basicConfig(level=logging.INFO)
        case 'DEBUG':
            logging.basicConfig(level=logging.DEBUG)
        case _:
            raise ValueError('Invalid log level')

    config = tomllib.load(config_file)
    evaluation_config = config['evaluation']
    combinations = []

    mode = evaluation_config['mode']
    in_race = False
    match mode:
        case 'normal':
            pass
        case 'race':
            in_race = True
        case _:
            raise ValueError('Invalid mode')

    for method in evaluation_config['methods']:
        for benchmark in evaluation_config['benchmarks']:
            if benchmark not in evaluation_config[method]['exclude']:
                combinations.append((benchmark, method))

    logger.info(f'Will run {", ".join(f"{b}_{m}" for b, m in combinations)}')
    existed = []
    for benchmark, method in combinations:
        dir_name = f'{benchmark}{DIR_SUFFIX[method]}'
        if os.path.exists(dir_name):
            existed.append((benchmark, method, dir_name))
    for b, m, d in existed:
        logger.error(f'{d} for {b}_{m} exists. Please remove it.')
        exit(-1)

    for benchmark, method in combinations:
        prepare_cmd = [
            'python', os.path.join(CWD, 'prepare.py'), benchmark, '-z', method
        ]
        subprocess.run(prepare_cmd, check=True, stderr=sys.stderr, stdout=sys.stdout)
        logger.info(f'{benchmark}_{method} prepared')

    all_start_time = datetime.now() # All time is the UTC time
    logger.info(f'Batch started at {all_start_time}; mode {mode}')
    for i, (benchmark, method) in enumerate(combinations):
        start_time = datetime.now()
        logger.info(f'Starting {benchmark}_{method} [{i}/{len(combinations)}] at {start_time}')
        run_cmd = ['xonsh', os.path.join(CWD, 'run.xsh')] + PRESETS[method][benchmark]
        # run_cmd += ['-j', '60', '-t', TIME_LIMIT, '-z', method, '-c', CHECKPOINT ,  benchmark]
        run_cmd += ['-j', '28', '-t', TIME_LIMIT, '-z', method, '-c', CHECKPOINT ,  benchmark]
        if in_race:
            run_cmd += ['--race-mode']
        subprocess.run(run_cmd, check=True, stderr=sys.stderr, stdout=sys.stdout)
        end_time = datetime.now()
        logger.info(f'Finish {benchmark}_{method} [{i}/{len(combinations)}] at {end_time}')

        benchmark_elapsed = end_time - start_time
        all_elapsed = end_time - all_start_time

        logger.info(f'{benchmark}_{method} elapsed: {benchmark_elapsed}')
        logger.info(f'All elapsed: {all_elapsed}')

if __name__ == '__main__':
    main()
