import os
import os.path
from typing import Callable, Literal, TypeVar, Generic
from enum import Enum
from tqdm import tqdm
import subprocess
import sys
import logging
from idontwannadoresearch import MailLogger
import click as clk
import dill
from concurrent.futures import ProcessPoolExecutor
from io import FileIO
from pexpect import run

from itertools import combinations

T = TypeVar('T')

class Lattice(Generic[T]):
    def __init__(self, elements: set[T]) -> None:
        if len(elements) > 14:
            logger.warning(f'The number of elements is too large {len(elements)}')
        bottom = frozenset()
        subsets = {0: {bottom}}
        predecessors = {bottom: set()}
        for i in range(1, len(elements) + 1):
            for pre in subsets[i - 1]:
                for e in elements:
                    if e in pre:
                        continue
                    new_set = pre.union({e})
                    if i not in subsets:
                        subsets[i] = set()
                    if new_set in subsets[i]:
                        continue
                    subsets[i].add(new_set)
                    pre_predecessors = predecessors[pre]
                    inc_predecessors  = {new_set: pre_predecessors.union({pre}) for pre in pre_predecessors}
                    predecessors[new_set] = pre_predecessors.union(inc_predecessors).union({pre})
        self.elements = elements
        self.bottom = bottom
        self.predecessors = predecessors
        topo_order = []
        for i in range(1, len(elements) + 1):
            tmp = list(subsets[i])
            tmp.sort()
            topo_order.extend(tmp)
        self.subsets = topo_order
    def is_predecessor(self, a: frozenset[T], b: frozenset[T]) -> bool:
        return a in self.predecessors[b]

logger = logging.getLogger(__file__)
mailogger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml", logger)

CWD = os.path.dirname(__file__)
WORKDIR_ROOT = os.path.join(CWD, 'workdir')

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

BINARY_NAMES = {
    'libxml2': 'xml',
    'sqlite3': 'ossfuzz',
    'cpython3': 'fuzzer',
}

BENCHMARKS = [
    'libxml2',
    'cpython3',
    'sqlite3',
]

FUZZERS = [
    'elm',
    'grmr',
    'isla',
    'islearn',
    'glade'
]

EXCLUDES = []
# EXCLUDES = [("cpython3", "grmr")]

TIME_POINTS = [
    3600 * i for i in range(0, 25)
]

AbnormalTriageResult = Literal['NOT_CRASH', 'NOT_CRASH_WITH_INDIVIDUAL']
ABNORMAL_TRIAGE_RESULTS = ['NOT_CRASH', 'NOT_CRASH_WITH_INDIVIDUAL']

CollectBugFunction = Callable[[str, set[str] | None, float], tuple[Literal['CRASH', 'NORMAL', 'TIMEOUT'], set[str], set[str]]]

def initilize():
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (10 * 1024 * 1024, resource.RLIM_INFINITY))

STDERR_SIZE_LIMIT = 16 * 1024
def build_collect_bugs(binary: str, filtered_bug_file: str, env: dict[str, str]) -> CollectBugFunction:
    def collect_bugs(test_case: str, only_enable: set[str] | None, timeout=5.0) -> tuple[Literal['CRASH', 'NORMAL', 'TIMEOUT'], set[str], set[str]]:
        import os
        import subprocess
        from datetime import datetime
        import random
        import copy
        import tempfile
        import signal
        cmd = [
            binary, test_case
        ]
        filtered = set()
        nonlocal env
        env = copy.deepcopy(env)
        with open(filtered_bug_file, 'r') as f:
            for line in f:
                filtered.add(line.strip())
        if only_enable is not None:
            assert len(only_enable.intersection(filtered)) == 0
            env['FIXREVERTER'] = f'on {" ".join(only_enable)}'
        else:
            env['FIXREVERTER'] = f'off {" ".join(filtered)}'
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, env=env, preexec_fn=initilize)
        try:
           _, stderr_b = proc.communicate(timeout=timeout)
           stderr = stderr_b.decode('utf-8')
        except subprocess.TimeoutExpired as t:
            assert proc.stderr is not None
            stderr = proc.stderr.read(STDERR_SIZE_LIMIT).decode('utf-8')
            os.kill(proc.pid, 9)
            retcode = 'TIMEOUT'
        else:
            if proc.returncode == 0:
                return 'NORMAL', set(), set()
            retcode = 'CRASH'

        triggered = set()
        reached = set()
        for line in stderr.splitlines():
            lt = line.strip()
            if lt.startswith('triggered bug index '):
                bug = lt.split()[-1]
                triggered.add(bug)
            elif lt.startswith('reached bug index '):
                bug = lt.split()[-1]
                reached.add(bug)
        return retcode, triggered, reached
    return collect_bugs

def build_collect_bugs4python(binary: str, filtered_bug_file: str, env: dict[str, str]) -> CollectBugFunction:
    filtered = set()
    with open(filtered_bug_file, 'r') as f:
        for line in f:
            filtered.add(line.strip())
    def collect_bugs4python(test_case: str, only_enable: set[str] | None, timeout=5.0) -> tuple[Literal['NORMAL', 'CRASH', 'TIMEOUT'], set[str], set[str]]:
        import os
        import subprocess
        from datetime import datetime
        import tempfile
        import random
        import copy
        cmd = [
            binary, test_case
        ]
        old_env = os.environ.copy()
        nonlocal env
        env = copy.deepcopy(env)
        if only_enable is not None:
            assert len(only_enable.intersection(filtered)) == 0
            env['FIXREVERTER'] = f'on {" ".join(only_enable)}'
        else:
            env['FIXREVERTER'] = f'off {" ".join(filtered)}'
        os.environ.update(env)
        n = datetime.now().strftime('%Y%m%d%H%M%S')

        try:
            out, r = run(
                f'{binary} {test_case}', timeout=timeout, env=os.environ, withexitstatus=True
            )
        except subprocess.TimeoutExpired as t:
            retcode = 'TIMEOUT'
        else:
            if r == 0:
                return 'NORMAL', set(), set()
            retcode = 'CRASH'
        os.environ.update(old_env)
        stderr = out.decode('utf-8')

        triggered = set()
        reached = set()
        for line in stderr.splitlines():
            lt = line.strip()
            if lt.startswith('triggered bug index '):
                bug = lt.split()[-1]
                triggered.add(bug)
            elif lt.startswith('reached bug index '):
                bug = lt.split()[-1]
                reached.add(bug)
        return retcode, triggered, reached
    return collect_bugs4python


def triage_one_batch(test_cases: list[str],
                     pickled_collect_bugs: bytes,
                    #  pbar: tqdm | None = None,
                     pickled_persist_result: bytes | None = None,
                     pickled_load_cache: bytes | None = None) -> dict[str, set[str] | AbnormalTriageResult]:
    persist_result: Callable[[str, set[str] | AbnormalTriageResult], None] | None = \
        dill.loads(pickled_persist_result) if pickled_persist_result is not None else None
    load_cache: Callable[[str], set[str] | AbnormalTriageResult | None] | None = \
        dill.loads(pickled_load_cache) if pickled_load_cache is not None else None
    collect_bugs: CollectBugFunction = dill.loads(pickled_collect_bugs)
    result = {}
    for test_case in test_cases:
        try_load = load_cache(test_case) if load_cache is not None else None
        if try_load is not None:
            result[test_case] = try_load
            continue
        timeout = 5.0
        crash_or_timeout, triggered, _reached = collect_bugs(test_case, None, timeout)
        if crash_or_timeout == 'NORMAL':
            result[test_case] = 'NOT_CRASH'
            logger.warning(f'{test_case} does not crash')
            continue
        assert len(triggered) > 0, test_case
        individual_causes = set()
        lattice = Lattice(triggered)
        for subset in lattice.subsets:
            exclude = False
            for s in individual_causes:
                if lattice.is_predecessor(s, subset):
                    exclude = True
                    break
            if exclude:
                continue
            crash_or_timeout, _, _ = collect_bugs(test_case, subset, timeout)
            if crash_or_timeout:
                individual_causes.add(subset)
        if len(individual_causes) > 0:
            attempt_result = set()
            for s in individual_causes:
                attempt_result.update(s)
        else:
            logger.warning(f'{test_case} does not crash with individual causes {{{",".join(triggered)}}}')
            attempt_result = 'NOT_CRASH_WITH_INDIVIDUAL'
        if persist_result is not None:
            persist_result(test_case, attempt_result)
        result[test_case] = attempt_result
    return result

def triage_single_exp(
    afl_dir: str,
    pickled_collect_bugs: bytes,
    time_points: list[int],
    pickled_persist_result: bytes | None = None,
    pickled_load_cache: bytes | None = None,
    parallel: int = 1
) -> tuple[dict[str, set[str] | AbnormalTriageResult], list[set[str]]]:
    crash_dir = os.path.join(afl_dir, 'default', 'crashes')
    hang_dir = os.path.join(afl_dir, 'default', 'hangs')

    crash_files = [os.path.join(crash_dir, f) for f in os.listdir(crash_dir) if f != 'README.txt']
    hang_files = [os.path.join(hang_dir, f) for f in os.listdir(hang_dir) if f != 'README.txt']
    files = crash_files + hang_files

    crashes_with_time = []

    for f in files:
        try:
            tokens = f.split(',')
            if tokens[2].startswith('time:'):
                time_token = tokens[2]
            elif tokens[3].startswith('time:'):
                time_token = tokens[3]
            else:
                assert False, f'{f} does not have time token'
            crash_time = int(time_token.removeprefix('time:')) / 1000
            crashes_with_time.append((f, crash_time))
        except Exception as e:
            print(f"Error in {f}: {e=}")
            pass
    crashes_with_time.sort(key=lambda x: x[1])

    with tqdm(total=len(crashes_with_time), desc=f'Triage {os.path.basename(afl_dir)}') as pbar, \
         ProcessPoolExecutor(max_workers=parallel) as executor:
        current_test_cases = []

        bug_triage = {}
        bug_triggered = []
        for idx in range(len(time_points) + 1):
            if current_test_cases:
                batch_size = min(max(len(current_test_cases) // parallel, 1), 20)
                batches = [current_test_cases[i:(i+batch_size) if i < len(current_test_cases) - 1 else len(current_test_cases)] for i in range(0, len(current_test_cases), batch_size)]
                futures = []
                def update_pbar(progress: tqdm, x: int):
                    def __update(future):
                        progress.update(x)
                    return __update
                for batch in batches:
                    future = executor.submit(triage_one_batch, batch, pickled_collect_bugs, pickled_persist_result, pickled_load_cache)
                    future.add_done_callback(update_pbar(pbar, len(batch)))
                    futures.append(future)
                triggered_by_one = {}
                for future in futures:
                    try:
                        triggered_by_one.update(future.result())
                    except Exception as e:
                        print(f"Error in {afl_dir}: {e=}")
                        pass
                bug_triage.update(triggered_by_one)
                tmp = set()
                for v in triggered_by_one.values():
                    if isinstance(v, set):
                        tmp.update(v)
                bug_triggered.append(tmp)
            elif idx > 0:
                bug_triggered.append(set())
            if idx == len(time_points):
                break
            current_time_point = time_points[idx]
            current_test_cases = []
            while crashes_with_time and crashes_with_time[0][1] < current_time_point:
                current_test_case = crashes_with_time.pop(0)
                current_test_cases.append(current_test_case[0])
        return bug_triage, bug_triggered

def encode_filename(filename: str) -> str:
    import base64
    return 'F_' + base64.b64encode(filename.encode('utf-8')).decode('utf-8').replace('=', '_')
pickled_encode_filename = dill.dumps(encode_filename)

def build_persist_result(cache_dir: str, pickled_encode_filename: bytes):
    def __persist_result(test_case: str, result: set[str] | AbnormalTriageResult):
        import os
        import dill
        __encode_filename = dill.loads(pickled_encode_filename)
        file_name = __encode_filename(test_case)
        with open(os.path.join(cache_dir, file_name), 'w') as f:
            f.write(test_case + '\n')
            if isinstance(result, set):
                f.write('\n'.join(result))
            else:
                f.write(str(result))
    return __persist_result

def build_load_cache(cache_dir: str, pickled_encode_filename: bytes, abnormal_triage_results: list[str] = ABNORMAL_TRIAGE_RESULTS):
    def __load_cache(filename: str) -> set[str] | AbnormalTriageResult | None:
        import os
        import dill
        __encode_filename = dill.loads(pickled_encode_filename)
        cache_filename = __encode_filename(filename)
        cache_file = os.path.join(cache_dir, cache_filename)
        if not os.path.exists(cache_file):
            return None
        with open(cache_file, 'r') as f:
            lines = f.readlines()
            if len(lines) < 2:
                logger.warning(f'{cache_filename} does not have enough lines')
                return None
            assert lines[0].strip() == filename, f'{filename} does not match {lines[0]}'
            result_line = lines[1].strip()
            if result_line in abnormal_triage_results:
                return result_line # type: ignore
            else:
                result = set()
                for line in lines[1:]:
                    result.add(line.strip())
    return __load_cache

def triage(afl_root: str, output_dir, cache_dir: str | None = None, parallel: int = 1, load_cache: bool = False, force_rerun: list[str] = []):
    if cache_dir is not None:
        os.makedirs(cache_dir, exist_ok=True)
        persist_result = build_persist_result(cache_dir, pickled_encode_filename)
    else:
        persist_result = None
    if load_cache:
        assert cache_dir is not None
        load_cache_func = build_load_cache(cache_dir, pickled_encode_filename, ABNORMAL_TRIAGE_RESULTS)
    else:
        load_cache_func = None
    abnormals = []
    for benchmark in BENCHMARKS:
        binary = os.path.join(WORKDIR_ROOT, f'{benchmark}', BINARY_NAMES[benchmark])
        filtered_bug_file = os.path.join(WORKDIR_ROOT, f'{benchmark}', 'filtered_bugs_all')
        env = ENV[benchmark]
        collect_bugs = (
            build_collect_bugs(binary, filtered_bug_file, env) if benchmark != 'cpython3'
            else build_collect_bugs4python(binary, filtered_bug_file,env)
        ) if benchmark not in NO_CACHE else None
        # collect_bugs = build_collect_bugs(binary, filtered_bug_file, env)
        for fuzzer in FUZZERS:
            try:
                if (benchmark, fuzzer) in EXCLUDES:
                    continue

                if os.path.exists(os.path.join(output_dir, f'{benchmark}_{fuzzer}.txt')):
                    if f"{benchmark}_{fuzzer}" not in force_rerun:
                        print(f'{benchmark}_{fuzzer} already exists')
                        continue
                    else:
                        print(f'Force rerun {benchmark}_{fuzzer}')
                        load_cache_func = None

                if cache_dir is not None:
                    single_results, result = triage_single_exp(
                        os.path.join(afl_root, f'{benchmark}_{fuzzer}'),
                        dill.dumps(collect_bugs),
                        TIME_POINTS,
                        dill.dumps(persist_result) if persist_result is not None else None,
                        dill.dumps(load_cache_func) if load_cache_func is not None else None,
                        parallel=parallel
                    )
                    for k, v in single_results.items():
                        if not isinstance(v, set):
                            abnormals.append((k, v))
                output_file = os.path.join(output_dir, f'{benchmark}_{fuzzer}.txt')
                with open(output_file, 'w') as f:
                    for bugs in result:
                        if len(bugs) > 0:
                            f.write(','.join(bugs) + '\n')
                        else:
                            f.write('___\n')
            except:
                pass
    abnormals.sort(key=lambda x: x[0])
    if abnormals:
        pass # TODO
    with open(os.path.join(output_dir, 'abnormals.txt'), 'w') as f:
        for k, v in abnormals:
            f.write(f'[{v}] {k}\n')
NO_CACHE = set()

@clk.command()
@clk.option('--afl-root', '-i', type=clk.Path(exists=True), required=True)
@clk.option('--output', '-o', type=clk.Path(), required=True)
@clk.option('--parallel', '-j', type=int, required=False, default=1)
@clk.option('--use-cache', '-c', is_flag=True, default=False)
@clk.option('--force-rerun', type=str, default="")
def main(afl_root, output, parallel, use_cache, force_rerun):
    force_rerun_list = [token.strip() for token in force_rerun.split(',') if token.strip()]
    if 'NO_CACHE' in os.environ:
        NO_CACHE.update(os.environ['NO_CACHE'].strip(' '))
    if not os.path.exists(output):
        os.makedirs(output)
    cache_dir = os.path.join(output, 'cache')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    triage(afl_root, output, cache_dir, parallel, use_cache, force_rerun=force_rerun_list)

if __name__=='__main__':
    main()
