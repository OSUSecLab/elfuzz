import os.path
import os
import subprocess
import sys
import click as clk
from idontwannadoresearch import MailLogger, watch
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed, Future
from datetime import datetime

logger = logging.getLogger(__file__)
mailogger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml", logger)

CWD = os.path.dirname(__file__)
BINARY_ROOT = os.path.join(CWD, '..', 'binary')
WORKDIR_ROOT = os.path.join(CWD, '..', 'workdir')

BINARIES = {
    'libxml2': os.path.join(BINARY_ROOT, 'libxml2', 'xml'),
    're2': os.path.join(BINARY_ROOT, 're2', 'fuzzer'),
    'cpython3': os.path.join(WORKDIR_ROOT, 'cpython3', 'fuzzer'),
    'cvc5': os.path.join(WORKDIR_ROOT, 'cvc5', 'cvc5'),
    'sqlite3': os.path.join(BINARY_ROOT, 'sqlite3', 'ossfuzz'),
    'librsvg': os.path.join(BINARY_ROOT, 'librsvg', 'render_document_patched'),
    'jsoncpp': os.path.join(BINARY_ROOT, 'jsoncpp', 'jsoncpp_fuzzer')
}

ENV = {
    'libxml2': {},
    're2': {},
    'sqlite3': {},
    'cpython3': {
        'AFL_MAP_SIZE': '2097152'
    },
    'cvc5': {
        'AFL_MAP_SIZE': '2097152',
        'LD_LIBRARY_PATH': os.path.join(WORKDIR_ROOT, 'cvc5')
    },
    'librsvg': {
        'AFL_MAP_SIZE': '2097152',
        'AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES': '1',
        'AFL_SKIP_CPUFREQ': '1'
    },
    'jsoncpp': {}
}

DICT_ROOT = os.path.join(CWD, '..', 'afl_dict')

# XXX: `cargo-afl` adds extra flags to the command line of afl-fuzz in `cargo afl fuzz`, causing
#  inconsistency with `cargo afl showmap`. Therefore, we need to invoke `afl-fuzz` directly.
LIBRSVG_AFL = os.path.join(os.environ['HOME'], '.local', 'share', 'afl.rs',
                           'rustc-1.81.0-eeb90cd', 'afl.rs-0.15.10', 'afl',
                           'bin', 'afl-fuzz')

def run_afl_for_librsvg(input_dir, output_dir, binary, env, time, dict_files=[]):
    dict_options = []
    for f in dict_files:
        dict_options += ['-x', f]
    cmd = [
        LIBRSVG_AFL,
        '-i', input_dir,
        '-o', output_dir,
        '-V', str(time),
        '-t','5000'] + dict_options + [
        '--',
        binary,
    ]
    #mailogger.log(f'Running {" ".join(cmd)}')
    for key, value in env.items():
        os.environ[key] = value
    retcode = os.system(' '.join(cmd) + ' > /dev/null 2>&1')
    if retcode != 0:
        mailogger.log(f'cargo afl fuzz failed with return code {retcode}', ' '.join(cmd))
        sys.exit(1)

def run_afl_for_librsvg_showmap(input_dir, output_dir, binary, env, time, dict_files=[]):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    cmd = [
        'cargo', 'afl', 'showmap',
        '-i', input_dir,
        '-C',
        '-o', os.path.join(output_dir, 'cov'),
        '-t','5000',
        '--',
        binary,
    ]
    #mailogger.log(f'Running {" ".join(cmd)}')
    for key, value in env.items():
        os.environ[key] = value
    retcode = os.system(' '.join(cmd) + ' > /dev/null 2>&1')
    if retcode != 0:
        mailogger.log(f'cargo afl showmap failed with return code {retcode}', ' '.join(cmd))
        sys.exit(1)
    with open(os.path.join(output_dir, 'count'), 'w') as count_f, \
         open(os.path.join(output_dir, 'cov'), 'r') as cov_f:
        count = len(list(filter(lambda l: l.strip(), cov_f.readlines())))
        count_f.write(str(count))

def run_afl(input_dir, output_dir, binary, env, time, dict_files=[]):
    dict_options = []
    for f in dict_files:
        dict_options += ['-x', f]
    cmd = [
        'afl-fuzz',
        '-i', input_dir,
        '-o', output_dir,
        '-V', str(time),
        '-t', '5000',] + dict_options + [
        '--',
        binary, '@@'
    ]
    #mailogger.log(f'Running {" ".join(cmd)}')

    try:
        subprocess.run(cmd, check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # subprocess.run(cmd, check=True, env=env, stdout=sys.stdout, stderr=sys.stderr)
    except Exception as e:
        mailogger.log(f'afl-fuzz exception: {e}', ' '.join(cmd))
        sys.exit(1)

def run_afl_showmap(input_dir, output_dir, binary, env, time, dict_files=[]):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    cmd = [
        'afl-showmap',
        '-i', input_dir,
        '-C',
        '-o', os.path.join(output_dir, 'cov'),
        '-t', '5000',
        '--',
        binary, '@@'
    ]
    #mailogger.log(f'Running {" ".join(cmd)}')

    try:
        subprocess.run(cmd, check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        mailogger.log(f'afl-showmap exception: {e}', ' '.join(cmd))
        sys.exit(1)

    with open(os.path.join(output_dir, 'count'), 'w') as count_f, \
         open(os.path.join(output_dir, 'cov'), 'r') as cov_f:
        count = len(list(filter(lambda l: not l.strip(), cov_f.readlines())))
        count_f.write(str(count))

BENCHMARKS = [
    'libxml2',
    're2',
    'cpython3',
    'cvc5',
    'sqlite3',
    'librsvg',
    'jsoncpp'
]

FUZZERS = [
    'elm',
    'grmr',
    'isla',
    'islearn',
    'glade'
]

EXCLUDES = [('re2', 'islearn'), ('jsoncpp', 'islearn')]
NL = "\n"

@clk.command()
@clk.option('--time', '-t', type=int, required=False, default=3600)
@clk.option('--input', '-i', type=clk.Path(exists=True), required=True)
@clk.option('--output', '-o', type=str, required=True)
@clk.option('--prepare', '-p', is_flag=True, default=False)
@clk.option('--id', '-id', type=str, required=False, default=None)
@clk.option('--seeds-mode', '-s', is_flag=True, default=False)
@clk.option('--parallel', '-j', type=int, required=False, default=30)
@clk.option('--repeat-times', '-r', type=int, required=False, default=1)
@clk.option('--repeat-start', '-rs', type=int, required=False, default=1)
@clk.option('--start-offset', '-so', type=str, required=False, default='')
@clk.option('--more-excludes', '-e', type=str, required=False, default='')
@watch(mailogger, report_ok=True)
def main(time, input, output, prepare, id, seeds_mode, parallel, repeat_times, repeat_start, start_offset, more_excludes):
    for token in more_excludes.split(','):
        if not token.strip():
            continue
        benchmark, fuzzer = token.strip().split('_')
        if (benchmark, fuzzer) not in EXCLUDES:
            EXCLUDES.append((benchmark, fuzzer))
    to_check = set()
    for benchmark in BENCHMARKS:
        for fuzzer in FUZZERS:
            if (benchmark, fuzzer) in EXCLUDES:
                continue
            to_check.add(benchmark)
    for c in to_check:
        binary = BINARIES[c]
        if not os.path.exists(binary):
            mailogger.log(f'{binary} does not exist')
            continue

    if prepare:
        for fuzzer in FUZZERS:
            for benchmark in BENCHMARKS:
                if (benchmark, fuzzer) in EXCLUDES:
                    continue
                dir = os.path.join(input, benchmark, fuzzer)
                if id is None:
                    candidates = os.listdir(dir)
                    candidates.sort(reverse=True,key=lambda x: int(x.removesuffix('.tar.zst')))
                    file_name = os.path.join(dir, candidates[0])
                else:
                    file_name = os.path.join(dir, f'{id}.tar.zst')
                seed_file = file_name
                cmd = [
                    'tar', '--zstd', '-xf', seed_file, '-C', output
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return

    offsets = {}
    if start_offset:
        for start_offset in start_offset.split(','):
            if not start_offset.strip():
                continue
            benchmark_and_fuzzer, offset_s = start_offset.strip().split(' ')
            offset = int(offset_s)
            offsets[benchmark_and_fuzzer] = offset

    batches: list[list[tuple[str, str, int]]] = []
    current_batch = []
    for repeat in range(repeat_start, repeat_start + repeat_times):
        for fuzzer in FUZZERS:
            for benchmark in BENCHMARKS:
                if (benchmark, fuzzer) in EXCLUDES:
                    continue
                if (benchmark, fuzzer, repeat) in EXCLUDES:
                    continue
                if f'{benchmark}_{fuzzer}' in offsets:
                    offset = offsets[f'{benchmark}_{fuzzer}']
                    if offset == -1 or repeat - repeat_start < offset:
                        continue
                if len(current_batch) == parallel:
                    batches.append(current_batch)
                    current_batch = []
                current_batch.append((benchmark, fuzzer, repeat))
    if current_batch:
        batches.append(current_batch)

    mailogger.log(f"Experiment started, {len(batches)=}", f'{NL.join(str(batch) for batch in batches)}')

    def callback(benchmark, fuzzer, repeat):
        message = f'{benchmark}_{fuzzer} [{repeat} / {repeat_times + repeat_start - 1}] finished'
        return lambda future: mailogger.log(message)
    with ProcessPoolExecutor(max_workers=parallel) as executor:
        mailogger.log(f"Experiment started, {len(batches)=}", f'{NL.join(str(batch) for batch in batches)}')

        experiment_start = []
        prestart_futures: list[Future[None]] = []
        def start_experiment(benchmark, fuzzer, repeat, futures: list[Future[None]], experiment_start: list[str]):
            dict_dir = os.path.join(DICT_ROOT, benchmark)
            dict_files = [os.path.join(dict_dir, f) for f in os.listdir(dict_dir)]
            ts = datetime.now()
            experiment_start.append('=====')
            experiment_start.append(
                f'{benchmark}_{fuzzer} [{repeat} / {repeat_start + repeat_times - 1}] started at {ts.strftime("%Y-%m-%d %H:%M:%S")}'
            )
            experiment_start.append(f'-----')
            experiment_start.append('Dict files:')
            for f in dict_files:
                experiment_start.append(f)
            experiment_start.append('=====')
            input_dir = os.path.join(input, f'{benchmark}_{fuzzer}')
            output_root = output.replace('%d', str(repeat))
            if not os.path.exists(output_root):
                os.makedirs(output_root)
            output_dir = os.path.join(output_root, f'{benchmark}_{fuzzer}')
            binary = BINARIES[benchmark]
            env = ENV[benchmark]
            if "AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES" in os.environ:
                env['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = os.environ['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES']
            match benchmark:
                case 'librsvg':
                    fuzz_func = run_afl_for_librsvg_showmap if seeds_mode else run_afl_for_librsvg
                    future = executor.submit(
                        fuzz_func, input_dir, output_dir, binary, env, time, dict_files
                    )
                case _:
                    fuzz_func = run_afl_showmap if seeds_mode else run_afl
                    future = executor.submit(
                        fuzz_func, input_dir, output_dir, binary, env, time, dict_files
                    )
            futures.append(future)
            future.add_done_callback(callback(benchmark, fuzzer, repeat))
        for idx in range(len(batches)):
            batch = batches[idx]
            # experiment_start.append(f'\n{len(prestart_futures)=}\n')
            if idx < len(batches) - 1:
                next_batch = batches[idx + 1]
            else:
                next_batch = []
            assert len(prestart_futures) <= parallel
            prestart_future_num = len(prestart_futures)
            futures: list[Future[None]] = list(prestart_futures)
            prestart_futures = []
            for benchmark, fuzzer, repeat in batch:
                start_experiment(benchmark, fuzzer, repeat, futures, experiment_start)
            assert len(futures) <= parallel
            mailogger.log(f'Batch {idx + 1}/{len(batches)} started', f'{len(batch)=}, {prestart_future_num=}\n' + '\n'.join(experiment_start))
            experiment_start = []
            for f in as_completed(futures):
                try:
                    f.result(timeout=time+3600 * 5)
                except TimeoutError:
                    pass
                if next_batch is not None and len(next_batch) > 0:
                    prestart = next_batch.pop(0)
                    start_experiment(*prestart, prestart_futures, experiment_start)
                    mailogger.log(f'Prestart {prestart=}', f'next_batch={idx + 2}/{len(batches)}')
                # mailogger.log(f'Batch {idx + 1}/{len(batches)} {completed}/{len(batch)} finished')
        # mailogger.log(f'{fuzzer} experiments finished')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
