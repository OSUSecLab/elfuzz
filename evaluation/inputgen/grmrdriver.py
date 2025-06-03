import logging
import click as clk
import os
import os.path
import importlib
import sys
import random
import io
from tempfile import TemporaryDirectory
import shutil
from datetime import datetime, timedelta
import concurrent.futures
import tqdm
import subprocess


logger = logging.getLogger(__file__)
CWD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CWD)
    

def wrapper(generator: str, outdir: str, file_prefix: str, num: int) -> timedelta:
    start_time = datetime.now()
    cmd = [
        'grammarinator-generate',
        '-o', os.path.join(outdir, f'{file_prefix}-%d.seed'),
        '-n', str(num),
        '-j', '1',
        '--sys-path', CWD,
        '-d', '10',
        f'{generator}.{generator}'
    ]
    subprocess.run(cmd, check=True)
    end_time = datetime.now()
    return end_time - start_time


class MyTmpDir(TemporaryDirectory):
    def __init__(self) -> None:
        super().__init__(ignore_cleanup_errors=True)
        self._rmtree = shutil.rmtree

import time
import threading
import signal
def start_process_to_terminate_when_parent_process_dies(ppid):
    pid = os.getpid()

    def f():
        while True:
            try:
                os.kill(ppid, 0)
            except OSError:
                os.kill(pid, signal.SIGTERM)
            time.sleep(1)

    thread = threading.Thread(target=f, daemon=True)
    thread.start()
    
BATCH_SIZE = 1000

@clk.command()
@clk.option('--generator', '-g', type=str, required=True)
@clk.option('--num', '-n', type=int, required=False, default=-1)
@clk.option('--debug-level', '-v', type=clk.Choice(['DEBUG', 'INFO']), required=False, default='INFO')
@clk.option('--size-limit', '-s', type=int, required=False, default=1024)
@clk.option('--para-num', '-j', type=int, required=False, default=32)
@clk.option('--output-dir', '-o', type=str, required=True)
@clk.option('--time', '-t', type=int, required=False, default=-1)
def main(generator, output_dir, num, debug_level, size_limit, para_num, time):
    assert not (num == -1 and time == -1)
    assert not (num != -1 and time != -1)
    
    if num != -1:
        num_for_each_process = num // para_num
        residue = num % para_num
        with concurrent.futures.ProcessPoolExecutor(max_workers=para_num) as executor:
            progress = tqdm.tqdm(total=num)
            futures = []
            index = {}
            for i in range(para_num - 1):
                f = executor.submit(wrapper, generator, output_dir, str(i), num_for_each_process)
                f.add_done_callback(lambda _: progress.update(num_for_each_process))
                futures.append(f)
                index[f] = i
            f = executor.submit(wrapper, generator, output_dir, str(para_num - 1), residue + num_for_each_process)
            f.add_done_callback(lambda _: progress.update(residue))
            futures.append(f)
            index[f] = para_num - 1
            
            # for i, f in map(lambda x: (x[0], concurrent.futures.as_completed(x[1])), futures):
            for f in concurrent.futures.as_completed(futures):
                f.result()
                i = index[f]
                logger.info(f'Process {i} finished')
            progress.close()
    if time != -1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=para_num) as executor:
            progress = tqdm.tqdm(total=time + 50)
            futures = []
            index = {}
            batch = 0
            time_sum = 0
            while time_sum < time:
                for i in range(para_num):
                    f = executor.submit(wrapper, 
                                        generator, 
                                        output_dir, 
                                        f'{batch}-{i}', 
                                        BATCH_SIZE)
                    futures.append(f)
                    index[f] = (batch, i)
                for f in concurrent.futures.as_completed(futures):
                    time_elapsed = f.result()

                    time_sum += time_elapsed.total_seconds()
                    progress.update(time_elapsed.total_seconds())
                    batch, i = index[f]
                    logger.info(f'Process {batch}-{i} finished')
                batch += 1
    
        
if __name__ == '__main__':
    main()
