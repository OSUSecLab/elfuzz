import click
import tempfile
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
from tqdm import tqdm

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

BENCHMARKS = [
    'libxml2',
    're2',
    'cpython3',
    'cvc5',
    'sqlite3',
    'librsvg',
    'jsoncpp'
]

USE_PRCS = [
    'libxml2',
    're2',
    'cpython3',
    'sqlite3',
    'jsoncpp'
]

FUZZER = 'glade'


def run_afl_showmap(input_dir, output_dir, binary, env) -> tuple[str, int]:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    cmd = [
        '/usr/bin/afl-showmap',
        '-i', input_dir,
        '-C',
        '-o', os.path.join(output_dir, 'cov'),
        '-t', '5000',
        '--',
        binary, '@@'
    ]

    try:
        ret = subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert ret.returncode == 0
    except Exception as e:
        print(f'Error: {" ".join(cmd)}\n{ret.returncode=}')
        sys.exit(1)

    with open(os.path.join(output_dir, 'cov'), 'r') as cov_f:
        cov_set = set([l.strip().split(':')[0] for l in cov_f.readlines() if l.strip()])
        cov_str = '\n'.join(cov_set)
        count = len(cov_set)
    return cov_str, count

def run_afl_for_librsvg_showmap(input_dir, output_dir, binary, env):
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
    for key, value in env.items():
        os.environ[key] = value
    retcode = os.system(' '.join(cmd) + ' > /dev/null 2>&1')
    if retcode != 0:
        print(f'Error: {" ".join(cmd)}')
        sys.exit(1)
    # with open(os.path.join(output_dir, 'count'), 'w') as count_f, \
    with open(os.path.join(output_dir, 'cov'), 'r') as cov_f:
        cov_set = set([l.strip().split(':')[0] for l in cov_f.readlines() if l.strip()])
        count = len(cov_set)
        cov_str = '\n'.join(cov_set)
    return cov_str, count

@click.command()
@click.option('--input', '-i', type=click.Path(exists=True, file_okay=False, dir_okay=True), required=True)
@click.option('--output', '-o', type=click.Path(exists=True, file_okay=False, dir_okay=True), required=True)
@click.option('--batch-size', '-b', type=int, required=False, default=1000)
def main(input, output, batch_size):
    for benchmark in BENCHMARKS:
        with tempfile.TemporaryDirectory(delete=False) as tmpd:
            if benchmark in USE_PRCS:
                seed_dir = os.path.join(input, f'{benchmark}_{FUZZER}', 'prcs')
            else:
                seed_dir = os.path.join(input, f'{benchmark}_{FUZZER}')

            all_seed_files = [f for f in os.listdir(seed_dir) if not (f.startswith('record_') or f.endswith('.txt'))]
            record_files = [f for f in os.listdir(seed_dir) if f.startswith('record_') and f.endswith('.txt')]

            record_points = []
            for record_file in record_files:
                seconds = int(record_file.split('_')[-1].split('.')[0])
                with open(os.path.join(seed_dir, record_file), 'r') as f:
                    content = f.read()
                    max_idx = int(content.strip())
                    record_points.append((seconds, max_idx))
            record_points.sort(key=lambda x: x[0])

            all_seed_files.sort(key=lambda x: int(x))

            current_min = 0
            next_idx = 0
            next_seconds, next_min = record_points[next_idx]

            seed_files_with_tag = []
            for seed_file in all_seed_files:
                if next_min is None:
                    assert next_seconds == 600
                    seed_files_with_tag.append((seed_file, 600))
                elif current_min <= int(seed_file) < next_min:
                    seed_files_with_tag.append((seed_file, next_seconds))
                else:
                    if next_idx < len(record_points) - 1:
                        current_min = next_min
                        next_idx += 1
                        next_seconds, next_min = record_points[next_idx]
                        seed_files_with_tag.append((seed_file, next_seconds))
                    else:
                        # seed_files_with_tag.append((seed_file, 600.0))
                        current_min = next_min
                        next_idx += 1
                        next_seconds = 600
                        next_min = None
                        seed_files_with_tag.append((seed_file, next_seconds))
            collect_file: dict[float, set[str]] = {}
            for seed_file, seconds in seed_files_with_tag:
                if seconds not in collect_file:
                    collect_file[seconds] = []
                collect_file[seconds].append(seed_file)

            batches = []
            for seconds, seed_files in collect_file.items():
                batches.append([])
                for seed_file in seed_files:
                    if len(batches[-1]) == batch_size:
                        batches.append([])
                    batches[-1].append((seconds, seed_file))
            print(f'{benchmark} starts with {len(batches)} batches')

            pbar = tqdm(total=len(batches))

            def callback(_message, pbar):
                def __callback(future):
                    pbar.update(1)
                return __callback

            futures = {}
            collect = {}
            with ThreadPoolExecutor(max_workers=20) as executor:
                for i, batch in enumerate(batches):
                    os.mkdir(os.path.join(tmpd, f'batch_{i}'))
                    os.mkdir(os.path.join(tmpd, f'batch_{i}', 'in'))
                    os.mkdir(os.path.join(tmpd, f'batch_{i}', 'out'))
                    seconds = None
                    for s, f in batch:
                        if seconds is None:
                            seconds = s
                        else:
                            assert seconds == s
                        shutil.copy(os.path.join(seed_dir, f), os.path.join(tmpd, f'batch_{i}', 'in', f))
                    future = executor.submit(run_afl_showmap if benchmark != 'librsvg' else run_afl_for_librsvg_showmap, os.path.join(tmpd, f'batch_{i}', 'in'), os.path.join(tmpd, f'batch_{i}', 'out'), BINARIES[benchmark], ENV[benchmark])
                    future.add_done_callback(callback(f'Batch {i} done', pbar))
                    futures[future] = seconds
                for future in as_completed(futures.keys()):
                    seconds = futures[future]
                    if seconds not in collect:
                        collect[seconds] = set()
                    cov_str, _count = future.result()
                    cov_sets = set(filter(lambda l: l.strip(), cov_str.split('\n')))
                    collect[seconds].update(cov_sets)
                pbar.close()
            output_count = os.path.join(output, f'{benchmark}_{FUZZER}_count.csv')
            with open(output_count, 'w') as f:
                f.write('Time,Count\n')
                cov_sets = set()
                for seconds, cov_sets1 in sorted(collect.items(), key=lambda x: x[0]):
                    cov_sets.update(cov_sets1)
                    f.write(f'{seconds},{len(cov_sets)}\n')
                    output_cov = os.path.join(output, f'{benchmark}_{FUZZER}_{seconds}.cov')
                    with open(output_cov, 'w') as fc:
                        fc.write('\n'.join(cov_sets))

if __name__ == '__main__':
    main()