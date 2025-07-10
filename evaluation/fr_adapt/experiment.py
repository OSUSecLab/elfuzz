import os.path
import os
import subprocess
import sys
import click as clk
from idontwannadoresearch import MailLogger, watch
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed, Future
import shutil
from datetime import datetime
logger = logging.getLogger(__file__)
mailogger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml", logger)

CWD = os.path.dirname(__file__)
WORKDIR_ROOT = os.path.join(CWD, 'workdir')
DICT_ROOT = os.path.join(CWD, '..', 'afl_dict')

BINARY_SOURCE = {
    'libxml2': os.path.join(CWD, 'libxml2', 'instrumented_bin', 'xml'),
    'cpython3': os.path.join(CWD, 'cpython3', 'instrumented_bin', 'injected.tar.xz'),
    'sqlite3': os.path.join(CWD, 'sqlite3', 'instrumented_bin', 'ossfuzz'),
}
ENV = {
    'libxml2': {},
    'sqlite3': {},
    'cpython3': {
        'AFL_MAP_SIZE': '2097152'
    },
}

BINARIES = {
    'libxml2': 'xml',
    'sqlite3': 'ossfuzz',
    'cpython3': 'fuzzer',
}

def run_afl(input_dir, output_dir, binary, env, time, dict_files=[], for_python=False, test_one=False):
    dict_options = []
    for f in dict_files:
        dict_options += ['-x', f]

    cmd = [
        'afl-fuzz',
        '-i', input_dir,
        '-o', output_dir,
        '-V', str(time),
        '-t', '5000',
    ] + dict_options + [
        '--',
        binary, '@@'
    ]
    # mailogger.log(f'Running {" ".join(cmd)}')

    if not for_python:
        try:
            if not test_one:
                subprocess.run(cmd, check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(cmd, check=True, env=env)
        except Exception as e:
            mailogger.log(f'afl-fuzz exception: {e}', ' '.join(cmd))
            sys.exit(1)
    else:
        os.environ.update(env)
        if not test_one:
            r = os.system(f'{" ".join(cmd)} 2>&1 > /dev/null')
        else:
            r = os.system(" ".join(cmd))
        if r != 0:
            mailogger.log(f'afl-fuzz retcode {r}', ' '.join(cmd))
            sys.exit(1)

BENCHMARKS = [
    'libxml2',
    'cpython3',
    'sqlite3',
]

FUZZERS = [
    'elm',
    # 'alt',
    'grmr',
    'isla',
    'islearn',
    "glade",
]

EXCLUDES = []

@clk.command()
@clk.option('--time', '-t', type=int, required=False, default=3600)
@clk.option('--input', '-i', type=clk.Path(exists=True), required=False)
@clk.option('--resume', '-r', is_flag=True, default=False)
@clk.option('--output', '-o', type=clk.Path(), default='-')
@clk.option('--prepare', '-p', is_flag=True, default=False)
@clk.option('--workdir', '-w', type=clk.Path(), default=WORKDIR_ROOT)
@clk.option('--id', '-id', type=str, default=None)
@clk.option('--repeat', '-R', type=int, default=10)
@clk.option('--test-one', '-T', type=str, default=None)
@clk.option('--parallel', '-j', type=int, default=25)
@clk.option('--start-batch', '-sb', type=int, default=None)
@clk.option('--end-batch', '-eb', type=int, default=None)
@clk.option('--more-excludes', '-e', type=str, default='')
@watch(mailogger, report_ok=True)
def main(time, input, output, prepare, resume, workdir, id, repeat, test_one, start_batch, end_batch,
         more_excludes, parallel):
    for token in more_excludes.split(','):
        if not token:
            continue
        benchmark, fuzzer = token.split('_')
        if (benchmark, fuzzer) in EXCLUDES:
            continue
        EXCLUDES.append((benchmark, fuzzer))
    if prepare:
        for binary in BINARY_SOURCE.values():
            if not os.path.exists(binary):
                mailogger.log(f'{binary} does not exist')
                continue
        for benchmark in BENCHMARKS:
            work_dir = os.path.join(workdir, benchmark)
            os.makedirs(work_dir, exist_ok=True)

            binary = BINARY_SOURCE[benchmark]
            if binary.endswith('.tar.xz'):
                cmd = [
                    'tar', '-xJf', binary, '-C', work_dir
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                shutil.copy(binary, work_dir)
            #shutil.copy(os.path.join(CWD, benchmark, 'filtered_bugs'), work_dir)
            shutil.copy(os.path.join(CWD, benchmark, 'filtered_bugs_all'), work_dir)

            if input is not None:
                for fuzzer in FUZZERS:
                    if (benchmark, fuzzer) in EXCLUDES:
                        continue
                    if id is None:
                        p = os.path.join(input, benchmark, fuzzer)
                        candidate_seed_files = [(f, int(f.removesuffix('.tar.zst'))) for f in os.listdir(p) if f.endswith('.tar.zst')]
                        assert len(candidate_seed_files) > 0
                        candidate_seed_files.sort(key=lambda x: x[1], reverse=True)
                        seed_file = os.path.join(p, candidate_seed_files[0][0])
                    else:
                        seed_file = os.path.join(input, benchmark, fuzzer, f'{id}.tar.zst')

                    if not os.path.exists(seed_file):
                        mailogger.log(f'{seed_file} does not exist')
                    cmd = [
                        'tar', '--zstd', '-xf', seed_file, '-C', output
                    ]
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    def callback(benchmark, fuzzer):
        message = f'{benchmark}_{fuzzer} finished'
        return lambda future: mailogger.log(message)

    BATCH_SIZE = parallel
    original_batches = []
    if test_one is not None:
        batches = [[[0,] + list(test_one.split('_'))]]
    else:
        for i in range(repeat):
            if not original_batches:
                original_batches.append([])
            for fuzzer in FUZZERS:
                for benchmark in BENCHMARKS:
                    if (benchmark, fuzzer) in EXCLUDES:
                        continue
                    if len(original_batches[-1]) >= BATCH_SIZE:
                        original_batches.append([])
                    original_batches[-1].append((i, benchmark, fuzzer))
    if start_batch is not None and end_batch is not None:
        batches = original_batches[start_batch:end_batch + 1]
    elif start_batch is not None:
        batches = original_batches[start_batch:]
    elif end_batch is not None:
        batches = original_batches[:end_batch + 1]
    else:
        batches = original_batches

    print('Batches: ', len(original_batches))

    with ProcessPoolExecutor(max_workers=BATCH_SIZE) as executor:
        mailogger.log(f'Experiments started with {len(batches)} batches', f"Batch sizes: {', '.join([str(len(b)) for b in batches])}\n{start_batch=}, {end_batch=}")

        for batch_idx, batch in enumerate(batches):
            header = f'Batch {batch_idx + 1}/{len(batches)} started at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}:\n'
            message = ''

            futures: list[Future[None]] = []
            for i, benchmark, fuzzer in batch:
                terminal_msg = f'{benchmark}_{fuzzer} [{i + 1}/{repeat}] started\n'
                print(terminal_msg)
                dict_files = []
                dict_dir = os.path.join(DICT_ROOT, benchmark)

                for f in os.listdir(dict_dir):
                    dict_files.append(os.path.join(dict_dir, f))

                if (benchmark, fuzzer) in EXCLUDES:
                    continue
                logger.info(f'{benchmark}_{fuzzer} experiment started')
                input_dir = os.path.join(input, f'{benchmark}_{fuzzer}')
                output_root = output.replace('%d', str(i))
                output_dir = os.path.join(output_root, f'{benchmark}_{fuzzer}')
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                binary = BINARIES[benchmark]
                env = ENV[benchmark]
                if 'AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES' not in os.environ:
                    env['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = os.environ.get('AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES', '1')
                env['AFL_CRASHING_SEEDS_AS_NEW_CRASH'] = '1'

                filtered_bugs = list()
                with open(os.path.join(workdir, benchmark, 'filtered_bugs_all')) as file:
                    for l in file:
                        filtered_bugs.append(l.strip())
                fr_str = 'off ' + ' '.join(filtered_bugs)
                env['FIXREVERTER'] = fr_str

                bin_to_run = os.path.join(workdir, f'{benchmark}', binary)
                if not resume:
                    future = executor.submit(
                        run_afl, input_dir, output_dir, bin_to_run, env, time, dict_files, for_python=benchmark=='cpython3',
                        test_one=test_one is not None
                    )
                    message += f'{benchmark}_{fuzzer} [{i + 1}/{repeat}] started at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: {input_dir=} {output_dir=} {bin_to_run=} {env=} {time=} {dict_files=}\n'
                else:
                    future = executor.submit(
                        run_afl, '-', input_dir, bin_to_run, env, time, dict_files, for_python=benchmark=='cpython3',
                        test_one=test_one is not None
                    )
                    message += f'{benchmark}_{fuzzer} [{i + 1}/{repeat}] started at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}: input_dir="-" {output_dir=} {bin_to_run=} {env=} {time=} {dict_files=}\n'
                futures.append(future)
                future.add_done_callback(callback(benchmark, fuzzer))
            mailogger.log(header, message)
            for f in as_completed(futures):
                try:
                    f.result(timeout=time+3600 * 5)
                except TimeoutError:
                    pass
            message = f'Batch {batch_idx}/{len(batches)} finished\n'
            mailogger.log(message)
        mailogger.log(f'Experiments finished')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
