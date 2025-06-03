import os
import sys
import os.path
import click as clk
import subprocess
import tempfile
import importlib
import shutil
import logging
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import time
import random
from pexpect import run
import copy

logger = logging.getLogger(__file__)

# PARALLEL_NUM = 20
BATCH_SIZE = 10

g_powerful_mode = True

def wrapper(cmd, batch, env, timeout, conservative=True, analyze_mode=False) -> set[str] | tuple[dict[str, int], int]:
    global g_powerful_mode
    triggered = set() if not analyze_mode else dict()
    error = 0
    for testcase in batch:
        cmd_replaced = [c.replace('@@', testcase) for c in cmd]
        if not g_powerful_mode:
            try:
                p = subprocess.run(cmd_replaced, 
                                capture_output=True,
                                env=env,
                                timeout=timeout,
                                preexec_fn=initilize)
            except subprocess.TimeoutExpired as t:
                if t.stderr is not None:
                    stderr = t.stderr.decode('utf-8')
                else:
                    stderr = ''
                error += 1
            except Exception as e:
                sys.exit(-1)
            else:
                if p.returncode != 0:
                    error += 1
                    if p.stderr is not None:
                        stderr = p.stderr.decode('utf-8')
                else:
                    stderr = None
        else:
            old_env = copy.deepcopy(os.environ)
            os.environ.update(env)
            
            try:
                out, r = run(' '.join(cmd_replaced), timeout=timeout, withexitstatus=True, env=os.environ)
            except subprocess.TimeoutExpired as t:
                error += 1
            else:
                if r != 0:
                    error += 1
            os.environ = old_env
            stderr = out.decode('utf-8')
        if stderr is not None:
            added = set()
            for l in stderr.splitlines():
                lt = l.strip()
                if lt.startswith('triggered bug index '):
                    bug = lt.split()[-1]
                    if not analyze_mode:
                        assert isinstance(triggered, set)
                        triggered.add(bug)
                    else:
                        assert isinstance(triggered, dict)
                        tagged = f't/{bug}'
                        if tagged in added:
                            continue
                        added.add(tagged)
                        if tagged not in triggered:
                            triggered[tagged] = 0
                        triggered[tagged] += 1
                elif not conservative and lt.startswith('reached bug index '):
                    bug = lt.split()[-1]
                    if not analyze_mode:
                        assert isinstance(triggered, set)
                        triggered.add(bug)
                    else:
                        assert isinstance(triggered, dict)
                        tagged = f'r/{bug}'
                        if tagged in added:
                            continue
                        added.add(tagged)
                        if tagged not in triggered:
                            triggered[tagged] = 0
                        triggered[tagged] += 1
    if analyze_mode:
        assert isinstance(triggered, dict)
        return triggered, error
    else:
        assert isinstance(triggered, set)
        return triggered
def initilize():
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (10 * 1024 * 1024, resource.RLIM_INFINITY))

def one_iter(cmd: list[str], testcase_dir: str, previously_triggered: set[str], it: int = -1, timeout=5, 
             conservative=True, parallel_num=20, analyze_mode=False, filter='') -> set[str] | tuple[dict[str, int], int, int]:
    triggered = set() if not analyze_mode else dict()
    if not filter:
        testcases = [os.path.join(testcase_dir, f) for f in os.listdir(testcase_dir)]
    else:
        testcases = [os.path.join(testcase_dir, f) 
                     for f in os.listdir(testcase_dir) 
                     if f.split('_')[1] == filter]
    
    batches = [testcases[i:min(i+BATCH_SIZE, len(testcases))] for i in range(0, len(testcases), BATCH_SIZE)]
    error_count = 0
    
    with ProcessPoolExecutor(max_workers=parallel_num) as executor, \
         tqdm(total=len(testcases), desc=f'Iteration {it}') as process:
        futures = []
        for batch in batches: 
            f = executor.submit(wrapper, cmd, batch, {'FIXREVERTER': f'off {" ".join(previously_triggered)}'}, 
                                timeout, conservative, analyze_mode)
            def callback(size):
                def update(f):
                    nonlocal error_count
                    process.update(size)
                    if not analyze_mode:
                        assert isinstance(f.result(), set)
                        assert isinstance(triggered, set)
                        triggered.update(f.result())
                    else:
                        assert isinstance(f.result(), tuple)
                        assert isinstance(triggered, dict)
                        triggered_batch, error = f.result()
                        error_count += error
                        for k, v in triggered_batch.items():
                            if k not in triggered:
                                triggered[k] = 0
                            triggered[k] += v
                return update
            f.add_done_callback(callback(len(batch)))
            futures.append(f)
        for f in as_completed(futures):
            _ = f.result()

    if not analyze_mode:
        assert isinstance(triggered, set)
        return triggered
    else:
        assert isinstance(triggered, dict)
        return triggered, error_count, len(testcases)

@clk.command()
@clk.option('--cmd', '-c', required=True, help='Command to run', type=str)
@clk.option('--testcase_dir', '-i', required=True, help='Testcase directory', type=clk.Path(exists=True, dir_okay=True, file_okay=False))
@clk.option('--output', '-o', required=True, help='Output file', type=clk.Path(dir_okay=False, writable=True, file_okay=True), default='-')
@clk.option('--conservative', '-C', help='Use conservative mode', default=False)
@clk.option('--parallel_num', '-j', help='Number of parallel processes', default=20)
@clk.option('--analyze-mode', '-A', help='Analyze mode', default=False, is_flag=True)
@clk.option('--forbid-from-file', '-FF', type=clk.Path(exists=True, dir_okay=False, file_okay=True), default=None)
@clk.option('--forbid', '-F', type=str, default='')
@clk.option('--filter', '-l', type=str, default='')
@clk.option('--powerful-mode', '-P', is_flag=True, default=False)
def main(cmd, testcase_dir, output, conservative, parallel_num, analyze_mode, forbid, forbid_from_file, filter, powerful_mode):
    global g_powerful_mode
    g_powerful_mode = powerful_mode
    count = 0
    result = set()
    if forbid_from_file is not None:
        with open(forbid_from_file, 'r') as f:
            forbidden_bugs = set(b.strip() for b in f)
    else:
        forbidden_bugs = set(b.strip() for b in forbid.split(','))
    result.update(forbidden_bugs)

    if analyze_mode:
        triggered, error_count, num = one_iter(cmd.split(), testcase_dir, result, count,
                                               conservative=conservative, parallel_num=parallel_num, 
                                               analyze_mode=True, filter=filter)
        assert isinstance(triggered, dict)
        assert isinstance(error_count, int)
        assert isinstance(num, int)
        with open(output, 'w') as f:
            print(f'{error_count}/{num}', file=f)
            t_tagged = []
            r_tagged = []
            for k, v in triggered.items():
                if k.startswith('t/'):
                    t_tagged.append((k, v))
                elif k.startswith('r/'):
                    r_tagged.append((k, v))
            for k, v in sorted(t_tagged, key=lambda x: x[1], reverse=True) + sorted(r_tagged, key=lambda x: x[1], reverse=True):
                print(f'{k}: {v}/{num}', file=f)
        return
    
    while True:
        count += 1
        triggered = one_iter(cmd.split(), testcase_dir, result, count, conservative=conservative, parallel_num=parallel_num)
        logging.info(f'Iteration {count}: {len(triggered)} triggered')
        if len(triggered) == 0:
            break
        result.update(triggered)
    print(f'num: {len(result)}')
    if output != '-':
        with open(output, 'w') as f:
            f.write('\n'.join(result))
    else:
        print('\n'.join(result))

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
