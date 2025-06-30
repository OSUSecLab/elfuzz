from idontwannadoresearch.mapreduce import project, segment, mapping, accumulate
from typing import Callable
import os
import os.path
import random
from idontwannadoresearch import MailLogger, watch
import click as clk
from tqdm import tqdm
import sys

BATCH_SIZE = 1000

def process(file_list: list[str],
            process_batch: Callable[[list[str]], list[str]],
            para_num: int, progress_bar: tqdm) -> list[str]:
    batch_num = max(len(file_list) // BATCH_SIZE, 1)

    return (
        project(file_list) >>
        segment(batch_num) >>
        mapping(process_batch, para_num=para_num, callback=lambda args, _future: progress_bar.update(len(args))) >> # type: ignore
        accumulate(lambda lists: [item for sublist in lists for item in sublist]) # type: ignore
    )

def __process_batch_prepend_data(prepend: Callable[[], bytes]):
    def __process_batch(out_dir: str) -> Callable[[list[str]], list[str]]:
        def __inner(batch: list[str]) -> list[str]:
            results = []
            for file in batch:
                with open(file, 'rb') as f:
                    data = f.read()
                file_name = os.path.basename(file)
                base_name = os.path.basename(file_name)
                with open(os.path.join(out_dir, file_name), 'wb') as f:
                    if not (base_name.startswith('record_') and base_name.endswith('.txt')):
                        f.write(prepend())
                    else:
                        print(f'Skip {file_name}')
                    f.write(data)
                results.append(os.path.join(out_dir, file_name))
            return results
        return __inner
    return __process_batch

from tempfile import TemporaryDirectory
import shutil
import subprocess

def __process_batch_libxml2(gen_seed: str):
    def __inner(out_dir: str) -> Callable[[list[str]], list[str]]:
        def __process_batch(batch: list[str]):
            results = []
            with TemporaryDirectory() as temp_dir:
                in_dir = os.path.join(temp_dir, 'in')
                __out_dir = os.path.join(temp_dir, 'seed', 'xml')
                os.makedirs(in_dir)
                os.makedirs(__out_dir)
                record_files = []
                for file in batch:
                    base_name = os.path.basename(file)
                    if not (base_name.startswith('record_') and base_name.endswith('.txt')):
                        shutil.move(file, in_dir)
                    else:
                        print(f'Skip {file}')
                        record_files.append(file)
                cmd = [
                    gen_seed, 'xml', f'{in_dir}/*'
                ]
                subprocess.run(cmd, check=True, cwd=temp_dir, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
                for file in os.listdir(__out_dir):
                    shutil.move(os.path.join(__out_dir, file), out_dir)
                    results = [os.path.join(out_dir, file)]
                for file in record_files:
                    shutil.move(file, out_dir)
                    results.append(os.path.join(out_dir, file))
                shutil.rmtree(in_dir, ignore_errors=True)
                shutil.rmtree(__out_dir, ignore_errors=True)
            return results
        return __process_batch
    return __inner

import logging

logger = logging.getLogger(__file__)
mailoger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml", chained_logger=logger)

def process_one(benchmark, input_dir, output_dir):
    files = [os.path.join(input_dir, f) for f in os.listdir(input_dir)]
    cwd = os.path.dirname(__file__)

    gen_seed = os.path.join(cwd, '..', 'binary', 'libxml2', 'genSeed')
    process_batches = {
        'cpython3': __process_batch_prepend_data(lambda: b'\x02' + random.randbytes(1)),
        're2': __process_batch_prepend_data(lambda: random.randbytes(2)),
        'sqlite3': __process_batch_prepend_data(lambda: random.randbytes(1) + b'\n'),
        'libxml2': __process_batch_libxml2(gen_seed),
        'jsoncpp': __process_batch_prepend_data(lambda: random.randbytes(4)),
    }

    with tqdm(total=len(files)) as progress:
        process(files, process_batches[benchmark](output_dir), para_num=25, progress_bar=progress)

BENCHMARKS = [
    'libxml2',
    'sqlite3',
    're2',
    'cpython3',
    'jsoncpp',
]

FUZZERS = [
    'elm',
    'isla',
    'islearn',
    'alt',
    'grmr',
    'glade'
]

EXCLUDES = [('re2', 'islearn'), ('jsoncpp', 'islearn')]

import itertools

@clk.command()
@clk.option('--input-root', '-i', type=clk.Path(exists=True), required=True)
@clk.option('--output-root', '-o', type=clk.Path(), required=True)
@clk.option('--prepare', is_flag=True, default=False)
@clk.option('--tarball-id', '-id', type=str, default=None)
@clk.option('--more-excludes', type=str, default='')
@watch(logger=mailoger, report_ok=True)
def main(input_root, output_root, prepare, tarball_id, more_excludes):
    if more_excludes:
        more_excludes = more_excludes.split(',')
        for exclude in more_excludes:
            benchmark, fuzzer = exclude.split('_')
            EXCLUDES.append((benchmark, fuzzer))
    if prepare:
        logger.info('Prepare mode')
        # assert tarball_id is not None
        for benchmark, fuzzer in itertools.product(BENCHMARKS, FUZZERS):
            if (benchmark, fuzzer) in EXCLUDES:
                continue
            if tarball_id is None:
                candidates = [f for f in os.listdir(os.path.join(input_root, benchmark, fuzzer)) if f.endswith(".tar.zst")]
                candidates.sort(key=lambda f: int(f.removesuffix(".tar.zst")), reverse=True)
                tarball_id = candidates[0].removesuffix(".tar.zst")
            input_file = os.path.join(input_root, benchmark, fuzzer, f'{tarball_id}.tar.zst')
            output_dir = output_root
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            cmd = ['tar', '-v', '--zstd', '-xf', input_file, '-C', output_dir]
            subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr, check=True)
            mailoger.log(f'Prepare {benchmark}_{fuzzer} done')
        return

    for benchmark, fuzzer in itertools.product(BENCHMARKS, FUZZERS):
        if (benchmark, fuzzer) in EXCLUDES:
            continue
        if benchmark == 'libxml2':
            logger.warning(f'Processing libxml2_{fuzzer} will remove the original file to save space')
        if fuzzer == 'glade':
            input_dir = os.path.join(input_root, f'{benchmark}_{fuzzer}')
        else:
            input_dir = os.path.join(input_root, f'{benchmark}_{fuzzer}', 'seeds')
        output_dir = os.path.join(output_root, f'{benchmark}_{fuzzer}', 'prcs')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        process_one(benchmark, input_dir, output_dir)
        mailoger.log(f'{benchmark}_{fuzzer} done')
        output_file = os.path.join(output_root, f'{benchmark}_{fuzzer}.tar.zst')
        cmd = ['tar', '--zstd', '-cf', output_file, '-C', output_root, f'{benchmark}_{fuzzer}']
        subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr, check=True)
        mailoger.log(f'{benchmark}_{fuzzer} tarball done')
        try:
            shutil.rmtree(output_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f'Error while deleting {output_dir}: {e}')
        mailoger.log(f'{benchmark}_{fuzzer} cleanup done')

if __name__ == '__main__':
    main()
