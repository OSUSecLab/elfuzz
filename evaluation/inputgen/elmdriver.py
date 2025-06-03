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


class RNG(io.BytesIO):
    def __init__(self, rand: random.Random) -> None:
        self.rand = rand
    
    # @override
    def read(self, size: int) -> bytes:
        return self.rand.randbytes(size)
    
    # @override
    def write(self, data: bytes) -> int:
        raise NotImplementedError()
    
    # @override
    def seek(self, offset: int, whence: int = 0) -> int:
        raise NotImplementedError()
    
    # @override
    def tell(self) -> int:
        raise NotImplementedError()
class SizedWriter(io.BufferedWriter):
    def __init__(self, underline: io.BufferedWriter, size_limit: int) -> None:
        self.__underline = underline
        self.__size_limit = size_limit
        self.__count = 0
    
    def write(self, data: bytes) -> int:
        if self.__count + len(data) > self.__size_limit:
            raise ValueError('Size limit exceeded')
        self.__count += len(data)
        return self.__underline.write(data)

logger = logging.getLogger(__file__)

g_size_limit = 1024

def wrapper(module_names: list[str], function: str, outdir: str, file_prefix: str, num: int) -> tuple[int, timedelta]:
    start_time = datetime.now()
    rng = RNG(random.Random())
    modules = []
    
    for module in module_names:
        tmp = importlib.import_module(module)
        modules.append(tmp)
    
    global g_size_limit
    
    error_count = 0
    for i in range(num):
        f_module = random.choice(modules)
        fuzzer = getattr(f_module, function)
        with open(os.path.join(outdir, f'{file_prefix}-{i}.seed'), 'wb') as f:
            try:
                fuzzer(rng, SizedWriter(f, g_size_limit))
            except Exception as e:
                logger.debug(f'Error in {module}.{function} ({outdir}/{file_prefix}-{i}.seed): {e}')
                error_count += 1
    end_time = datetime.now()
    return error_count, end_time - start_time


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
@clk.option('--function', '-g', type=str, required=True)
@clk.option('--num', '-n', type=int, required=False, default=-1)
@clk.option('--debug-level', '-v', type=clk.Choice(['DEBUG', 'INFO']), required=False, default='INFO')
@clk.option('--size-limit', '-s', type=int, required=False, default=1024)
@clk.option('--para-num', '-j', type=int, required=False, default=32)
@clk.option('--output-dir', '-o', type=str, required=True)
@clk.option('--time', '-t', type=int, required=False, default=-1)
def main(function, output_dir, num, debug_level, size_limit, para_num, time):
    assert not (num == -1 and time == -1)
    assert not (num != -1 and time != -1)
    
    cwd = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, cwd)
    
    fuzzer_module_names: list[str] = []
    for f in os.listdir(cwd):
        if f.endswith('.py') and f.startswith('gen'):
            module = f[:-3]
            fuzzer_module_names.append(module)
        elif f == 'get_cov.py':
            pass
    if num != -1:
        num_for_each_process = num // para_num
        residue = num % para_num
        with RNG(random.Random()) as rng, \
            concurrent.futures.ProcessPoolExecutor(max_workers=para_num) as executor:
            progress = tqdm.tqdm(total=num)
            futures = []
            index = {}
            for i in range(para_num - 1):
                f = executor.submit(wrapper, fuzzer_module_names, function, output_dir, str(i), num_for_each_process)
                f.add_done_callback(lambda _: progress.update(num_for_each_process))
                futures.append(f)
                index[f] = i
            f = executor.submit(wrapper, fuzzer_module_names, function, output_dir, str(para_num - 1), residue + num_for_each_process)
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
        with RNG(random.Random()) as rng, \
            concurrent.futures.ProcessPoolExecutor(max_workers=para_num) as executor:
            progress = tqdm.tqdm(total=time + 50)
            futures = []
            index = {}
            batch = 0
            time_sum = 0
            while time_sum < time:
                for i in range(para_num):
                    f = executor.submit(wrapper, 
                                        fuzzer_module_names, 
                                        function, 
                                        output_dir, 
                                        f'{batch}-{i}', 
                                        BATCH_SIZE)
                    futures.append(f)
                    index[f] = (batch, i)
                for f in concurrent.futures.as_completed(futures):
                    error_count, time_elapsed = f.result()

                    time_sum += time_elapsed.total_seconds()
                    progress.update(time_elapsed.total_seconds())
                    batch, i = index[f]
                    logger.info(f'Process {batch}-{i} finished')
                batch += 1
            
    
        
if __name__ == '__main__':
    main()
