import click as clk
from idontwannadoresearch import MailLogger, watch
from idontwannadoresearch.mapreduce import project, mapping, segment, accumulate
import logging
import itertools
import random
import tempfile
import os
import os.path
import sys
import subprocess
import shutil
from tqdm import tqdm

logger = logging.getLogger(__file__)
mailogger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml", chained_logger=logger)


BENCHMAKRS = [
    're2',
    'libxml2',
    'cpython3',
    'sqlite3',
    'cvc5',
    'librsvg',
    'jsoncpp'
]

# Fuzzers elm, alt, isla, and islearn will prepend metadata during generation.
# libxml2 uses a special mechanism and we will make sure that its metadata is prepended.
USE_PRCS=[('sqlite3', 'grmr'), ('re2', 'grmr'), ('cpython3', 'grmr'), ('jsoncpp', 'grmr'),
          ('libxml2', 'glade'), ('sqlite3', 'glade'), ('re2', 'glade'), ('cpython3', 'glade'), ('jsoncpp', 'glade')]

FUZZERS = ['elm', 'alt', 'grmr', 'isla', 'islearn', 'glade']
# FUZZERS = ['glade']

EXCLUDE = [('re2', 'islearn'), ('jsoncpp', 'islearn')]

CWD = os.path.dirname(__file__)

BINARY_DIR = os.path.join(CWD, '..', 'binary')

WORK_DIR = os.path.join(CWD, '..', 'workdir')

BINARIES = {
    're2': os.path.join(BINARY_DIR, 're2', 'fuzzer'),
    'libxml2': os.path.join(BINARY_DIR, 'libxml2', 'xml'),
    'sqlite3': os.path.join(BINARY_DIR, 'sqlite3', 'ossfuzz'),
    'cpython3': os.path.join(WORK_DIR, 'cpython3', 'fuzzer'),
    'cvc5': os.path.join(WORK_DIR, 'cvc5', 'cvc5'),
    'librsvg': os.path.join(BINARY_DIR, 'librsvg', 'render_document_patched'),
    'jsoncpp': os.path.join(BINARY_DIR, 'jsoncpp', 'jsoncpp_fuzzer')
}

ENV = {
    'libxml2': {},
    're2': {},
    'sqlite3': {},
    'jsoncpp': {},
    'cpython3': {
        'AFL_MAP_SIZE': '2097152'
    },
    'cvc5': {
        'AFL_MAP_SIZE': '2097152',
        'LD_LIBRARY_PATH': os.path.join(WORK_DIR, 'cvc5')
    },
    'librsvg': {
        'AFL_MAP_SIZE': '2097152',
        'AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES': '1',
        'AFL_SKIP_CPUFREQ': '1'
    }
}

def process_batch(binary: str, env: dict[str, str], root_dir: str, move_instead_of_copy=False):
    def __process(batch: list[str]) -> list[str]:
        if not batch[0].endswith('.seed'):
            batch_id = os.path.basename(batch[0])
        else:
            batch_id, ext = os.path.basename(batch[0]).split('.')
            assert ext == 'seed'
        batch_dir = os.path.join(root_dir, f'in{batch_id}')
        if not os.path.exists(batch_dir):
            os.makedirs(batch_dir)
        for seed_file in batch:
            if move_instead_of_copy:
                shutil.move(seed_file, batch_dir)
            else:
                shutil.copy(seed_file, batch_dir)
        batch_output_dir = os.path.join(root_dir, f'out{batch_id}')
        os.makedirs(batch_output_dir)
        cmd = ['afl-cmin', '-A', '-i', batch_dir, '-o', batch_output_dir, '--', binary, '@@']
        try:
            subprocess.run(cmd, check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.warning(f'afl-cmin exception: {e}')
        return [os.path.join(batch_output_dir, f) for f in os.listdir(batch_output_dir)]
    return __process

def process_batch_librsvg(binary: str, env: dict[str, str], root_dir: str, move_instead_of_copy=False):
    def __process(batch: list[str]) -> list[str]:
        if not batch[0].endswith('.seed'):
            batch_id = os.path.basename(batch[0])
        else:
            batch_id, ext = os.path.basename(batch[0]).split('.')
            assert ext == 'seed'
        batch_dir = os.path.join(root_dir, f'in{batch_id}')
        if not os.path.exists(batch_dir):
            os.makedirs(batch_dir)
        for seed_file in batch:
            if move_instead_of_copy:
                shutil.move(seed_file, batch_dir)
            else:
                shutil.copy(seed_file, batch_dir)
        batch_output_dir = os.path.join(root_dir, f'out{batch_id}')
        os.makedirs(batch_output_dir)
        cmd = [
            'cargo', 'afl', 'cmin', '-A', '-i', batch_dir, '-o', batch_output_dir, '--', binary
        ]
        os.environ.update(env)
        os.system(' '.join(cmd) + ' >/dev/null 2>&1')
        try:
            shutil.rmtree(batch_dir, ignore_errors=True)
        except:
            pass
        return [os.path.join(batch_output_dir, f) for f in os.listdir(batch_output_dir)]
    return __process

def sum(out_dir: str):
    def __sum(batch_results: list[list[str]]) -> list[str]:
        for batch_result in batch_results:
            for seed_file in batch_result:
                shutil.move(seed_file, out_dir)
        return [os.path.join(out_dir, f) for f in os.listdir(out_dir)]
    return __sum

def process(benchmark, fuzzer, batch_size, file_list, root, output, progress: tqdm, move_instead_of_copy=False) -> list[str]:
    process = process_batch if benchmark != 'librsvg' else process_batch_librsvg
    binary = BINARIES[benchmark]
    env = ENV[benchmark]
    root_dir = os.path.join(root)

    seg_num = max(1, len(file_list) // batch_size)

    def callback(args, future):
        progress.update(len(args))

    return (
        project(file_list) >>
        segment(seg_num) >>
        mapping(process(binary, env, root_dir, move_instead_of_copy=move_instead_of_copy), 30, callback) >> # type: ignore
        accumulate(sum(output)) # type: ignore
    )

@clk.command()
@clk.option('--shuffle', '-r', is_flag=True, default=False)
@clk.option('--batch-size', '-b', default=1000)
@clk.option('--id', '-id', type=str)
@clk.option('--input', '-i', type=clk.Path(exists=True, dir_okay=True, file_okay=False))
@clk.option('--output', '-o', type=clk.Path(dir_okay=True, file_okay=False, exists=False))
@clk.option('--iteration', '-it', type=int, default=1)
@clk.option('--first-run', '-1', is_flag=True, default=False)
@clk.option('--move-instead-of-copy', '-m', is_flag=True, default=False)
@clk.option('--last-run', '-l', is_flag=True, default=False)
@clk.option('--more-excludes', '-e', type=str, default="")
@watch(mailogger, report_ok=True)
def main(shuffle, batch_size, id, input, output, iteration, first_run, move_instead_of_copy, last_run, more_excludes):
    logging.basicConfig(level=logging.INFO)
    if more_excludes:
        more_excludes = more_excludes.split(',')
        for exclude in more_excludes:
            benchmark, fuzzer = exclude.split('_')
            EXCLUDE.append((benchmark, fuzzer))
    for benchmark, fuzzer in itertools.product(BENCHMAKRS, FUZZERS):
        if (benchmark, fuzzer) in EXCLUDE:
            continue
        if first_run:
            if (benchmark, fuzzer) not in USE_PRCS:
                seed_file = os.path.join(input, 'raw_seeds', benchmark, fuzzer, f'{id}.tar.zst')
            else:
                seed_file = os.path.join(input, 'prcs', benchmark, fuzzer, f'{id}.tar.zst')
            if not os.path.exists(seed_file):
                mailogger.log(f'File check error', f'{seed_file}')
                sys.exit(-1)
        else:
            seed_dir = os.path.join(input, 'cmin', f'{benchmark}_{fuzzer}')
            if not os.path.exists(seed_dir):
                mailogger.log(f'Dir check error', f'{seed_dir}')
                sys.exit(-1)
    for benchmark, binary in BINARIES.items():
        if (benchmark, fuzzer) in EXCLUDE:
            continue
        if not os.path.exists(binary):
            mailogger.log(f'Binary not found', f'{binary}')
            sys.exit(-1)

    for benchmark, fuzzer in itertools.product(BENCHMAKRS, FUZZERS):
        if (benchmark, fuzzer) in EXCLUDE:
            continue
        output_dir = os.path.join(output, str(iteration), 'cmin', f'{benchmark}_{fuzzer}')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        if (benchmark, fuzzer) not in USE_PRCS:
            seed_file = os.path.join(input, 'raw_seeds', benchmark, fuzzer, f'{id}.tar.zst')
        else:
            seed_file = os.path.join(input, 'prcs', benchmark, fuzzer, f'{id}.tar.zst')
        with tempfile.TemporaryDirectory() as td:
            if first_run:
                tmp_in = os.path.join(td, 'in_s')
                os.makedirs(tmp_in)
                cmd = ['tar', '-v', '--zstd', '-xf', seed_file, '-C', tmp_in]
                subprocess.run(cmd, check=True, stdout=sys.stdout, stderr=sys.stderr)
                mailogger.log(f'Extracted {seed_file}', f'{td}')
                if (benchmark, fuzzer) in USE_PRCS:
                    seed_file_dir = os.path.join(tmp_in, f'{benchmark}_{fuzzer}', 'prcs')
                else:
                    if fuzzer == 'glade':
                        seed_file_dir = os.path.join(tmp_in, f'{benchmark}_{fuzzer}')
                    else:
                        seed_file_dir = os.path.join(tmp_in, f'{benchmark}_{fuzzer}', 'seeds')
                seed_files = [os.path.join(seed_file_dir, f) for f in os.listdir(seed_file_dir)]
            else:
                seed_file_dir = os.path.join(input, 'cmin', f'{benchmark}_{fuzzer}')
                tmp_in = seed_file_dir
                seed_files = [os.path.join(tmp_in, f) for f in os.listdir(tmp_in) if not (f.startswith('record_') and f.endswith('.txt'))]
            in_num = len(seed_files)
            if in_num < batch_size and not last_run:
                for seed_file in seed_files:
                    shutil.move(seed_file, output_dir)
                mailogger.log(f'{benchmark}_{fuzzer} skipped', f'{in_num} < {batch_size}')
                continue
            if shuffle:
                random.shuffle(seed_files)

            tmp_out = os.path.join(td, 'out_s')
            os.makedirs(tmp_out)
            with tqdm(total=in_num, desc=f'{benchmark}_{fuzzer}') as progress:
                if last_run:
                    actual_batch_size = in_num + 1
                else:
                    actual_batch_size = batch_size
                results = process(benchmark, fuzzer, actual_batch_size, seed_files, td, tmp_out, progress, move_instead_of_copy=first_run or move_instead_of_copy)
            result_num = len(results)
            for f in results:
                shutil.move(f, output_dir)
            mailogger.log(f'{benchmark}_{fuzzer} processed',
                          f'{in_num} -> {result_num}' +
                          f'\nargs: {benchmark=}, {fuzzer=}, {batch_size=}, {id=}, {iteration=}, {first_run=}, {shuffle=}, {output_dir=}' +
                          (f' {seed_file=}' if first_run else f' {seed_file_dir=}'))
            if in_num - result_num < batch_size and not last_run:
                mailogger.log(f'Warning: {benchmark}_{fuzzer} low reduction', f'{in_num=} - {result_num=} < {batch_size=}')

if __name__ == '__main__':
    main()
