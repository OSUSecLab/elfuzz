from pip._vendor import tomli as tomllib
import click as clk
import logging
import os
import os.path

logger = logging.getLogger(__file__)

PRESETS = {
    'zest': {
        'cpython3': [],
        'cvc5': ['-b', '1'],
        'librsvg': ['-b', '1000'],
        'sqlite3': [],
        'jsoncpp': [],
        'libxml2': [],
        're2': [],
    },
}

DIR_SUFFIX = {
    'zest': '_zest',
}

TIME_LIMIT = '100'
CHECKPOINT = '1'

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
            'python', os.path.join(CWD, 'prepare_zest.py'), benchmark
        ]
        subprocess.run(prepare_cmd, check=True, stderr=sys.stderr, stdout=sys.stdout)
        logger.info(f'{benchmark}_{method} prepared')

    all_start_time = datetime.now() # All time is the UTC time
    logger.info(f'Batch started at {all_start_time}; mode {mode}')
    for i, (benchmark, method) in enumerate(combinations):
        start_time = datetime.now()
        logger.info(f'Starting {benchmark}_{method} [{i}/{len(combinations)}] at {start_time}')
        run_cmd = ['xonsh', os.path.join(CWD, 'run.xsh'), '-f'] + PRESETS[method][benchmark]
        run_cmd += ['-j', '60', '-t', TIME_LIMIT, '-z', method, '-c', CHECKPOINT ,  benchmark]
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
