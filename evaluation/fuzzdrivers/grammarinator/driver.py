import logging
import click as clk
import os
import os.path
import importlib
import sys
import random
import io
# from typing import override
from tempfile import TemporaryDirectory
import shutil
from datetime import datetime
import concurrent.futures
import subprocess
# import multiprocessing


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

def wrapper(workdir: str, generator: str, outdir: str, num: int, timeout: int) -> int:
    MAX_DEPTH = 10
    cmd = [
        'grammarinator-generate',
        '-o', f'{outdir}/%d.seed',
        '-d', str(MAX_DEPTH),
        '-j', '1',
        '--sys-path', workdir,
        '-n', str(num),
        generator,
    ]
    subprocess.run(cmd, check=True, stderr=sys.stderr, stdout=sys.stdout, timeout=timeout)
    return 0

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

# prepend, actually
def append_metadata(callback: str, batch_dir: str):
    cb_module = importlib.import_module(callback)
    preprocess = getattr(cb_module, 'preprocess')
    if preprocess is None:
        return
    seeds = os.listdir(batch_dir)
    with RNG(random.Random()) as rng:
        for seed in seeds:
            with open(os.path.join(batch_dir, seed), 'rb') as f:
                bytes = f.read()
            with open(os.path.join(batch_dir, seed), 'wb') as f:
                preprocess(rng, f)
                f.write(bytes)

def append_metadata_conc(callback: str | None, 
                    batches_start: int, 
                    batches_num: int, 
                    batches_root: str, 
                    paranum: int):
    if callback is None:
        return
    with concurrent.futures.ProcessPoolExecutor(max_workers=paranum) as executor:
        futures = []
        for i in range(batches_num):
            batch_dir = os.path.join(batches_root, f'{i+batches_start}')
            future = executor.submit(append_metadata, callback, batch_dir)
            futures.append(future)
        for future in concurrent.futures.as_completed(futures):
            future.result()
        executor.shutdown(wait=False)

@clk.command()
@clk.option('--generator', '-g', type=str, required=True)
@clk.option('--working-dir', '-d', type=clk.Path(exists=True, file_okay=False, dir_okay=True), required=False, default='.')
@clk.option('--num', '-n', type=int, required=False, default=-1)
@clk.option('--time-limit', '-t', type=int, required=False, default=-1, help="Time limit in seconds")
@clk.option('--force', '-f', is_flag=True, required=False, default=False)
@clk.option('--batch-size', '-b', type=int, required=False, default=1000)
@clk.option('--para-num', '-j', type=int, required=False, default=1)
@clk.option('--afl-dir', '-a', type=str, required=False, default='/usr/local/bin')
@clk.option('--callback', '-cb', type=str, required=False, default=None)
@clk.option('--debug-level', '-v', type=clk.Choice(['DEBUG', 'INFO']), required=False, default='INFO')
@clk.option('--race-mode', '-r', is_flag=True, required=False, default=False)
@clk.option('--stat-file', '-sf', type=clk.File('w'), required=False, default='-')
@clk.option('--check-point', '-c', type=int, required=False, default=-1)
def main(generator, working_dir, num, time_limit, force, batch_size, para_num, 
         afl_dir, callback, debug_level, race_mode, stat_file, check_point):
    target_name = os.path.basename(working_dir).split('_')[0]
    out_dir = os.path.join(working_dir, 'out')
    if race_mode:
        logger.warning(f'In race mode; write to {stat_file}.')
    # CPU_COUNT = multiprocessing.cpu_count()
    match debug_level:
        case 'INFO':
            logging.basicConfig(level=logging.INFO)
        case 'DEBUG':
            logging.basicConfig(level=logging.DEBUG)
        case _:
            raise ValueError('Invalid debug level')

    overall_start_time = datetime.now()
    if not force and os.path.exists(os.path.join(working_dir, 'sum.cov')):
        logger.warning('Coverage file already exists. Add --force to overwrite it.')
        return
    sys.path.insert(0, working_dir)
    cov_module = None
    for f in os.listdir(working_dir):
        if f == 'get_cov.py':
            cov_module = importlib.import_module(f[:-3])

    assert cov_module is not None
    if hasattr(cov_module, 'm_batch_size'):
        cov_module.m_batch_size = batch_size
    
    with MyTmpDir() as td, RNG(random.Random()) as rng, \
         concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
        count = 0
        batch = 0
        left = num if num > 0 else (2 ** 32 - 1)
        
        batch_acc = 0
        batch_record = 0

        time_sum = 0
        last_checkpoint = 0
        last_checkpoint_batch = 0
        while left > 0:
            elapsed_time = (datetime.now() - overall_start_time)
            logger.info(f'Total elapsed time: {elapsed_time}')
            logger.info(f'Fuzz batch {batch} ({batch_size} per batch)')
            logger.info(f'Current num: {count} / {num if num > 0 else "inf"}')
            logger.info(f'Time sum: {time_sum} / {time_limit if time_limit > 0 else "inf"}')
            
            if time_limit > 0 and time_sum > time_limit:
                break

            if check_point > 0 and time_sum - last_checkpoint > check_point:
                logger.info('Save checkpoint')
                with open(os.path.join(working_dir, f'cp_{time_sum}.cov'), 'w') as cp_f:
                    edge_count = {}
                    
                    if last_checkpoint > 0:
                        with open(os.path.join(working_dir, f'cp_{last_checkpoint}.cov'), 'r') as last_cp_f:
                            logger.debug(f'Load checkpoint {last_checkpoint}')
                            for l in last_cp_f:
                                (edge, hit) = l.strip().split(':')
                                edge_count[edge] = int(hit)
                    ###################
                    not_evaled = []
                    for i in range(last_checkpoint_batch, batch):
                        if not os.path.exists(os.path.join(td, f'{i}.cov')):
                            logger.warning(f'Batch {i} evaled')
                            not_evaled.append(i)
                    
                    start = not_evaled[0]
                    end = not_evaled[-1]
                    if not end + 1 - start == len(not_evaled):
                        logger.warning(f'Not evaled may have problem: {not_evaled}')
                    logger.info('Getting coverage')
                    if not race_mode:
                        try:
                            cov_module.get_cov_conc(working_dir, td, td, len(not_evaled), len(not_evaled), start, os.path.join(afl_dir, 'afl-showmap'))
                        except Exception as e:
                            logger.error(f'Err: {e}')
                    for i in not_evaled:
                        batch_dir = os.path.join(td, f'{i}')
                        try:
                            shutil.move(batch_dir, os.path.join(out_dir, f'{i}'))
                        except:
                            pass
                        if target_name == 'libxml2':
                            logger.info('Remove an extra tmp dir for libxml2')
                            tmp_dir = os.path.join(working_dir, f'{i}-tmp')
                            try:
                                shutil.move(tmp_dir, os.path.join(out_dir, f'{i}-tmp'))
                            except:
                                pass
                    batch_acc =0 
                    batch_record = batch
                    ###################
                    
                    for i in range(last_checkpoint_batch, batch):
                        logger.debug(f'Merging batch {i} / {batch - 1}')
                        try:
                            with open(os.path.join(td, f'{i}.cov'), 'r') as batch_cov:
                                total_lines = sum(1 for _ in batch_cov)
                                batch_cov.seek(0)
                                for ii, l in enumerate(batch_cov):
                                    logger.debug(f'Merging batch {ii + 1}/{total_lines} (in batch {i})')
                                    (edge, hit) = l.strip().split(':')
                                    if edge in edge_count:
                                        edge_count[edge] += int(hit)
                                    else:
                                        edge_count[edge] = int(hit)
                        except Exception as e:
                            logger.error(f'Error in batch {i}: {e}')
                    logger.debug(f'Writing to checkpoint {time_sum}.cov')
                    total_items = len(edge_count)
                    for i, (edge, hit) in enumerate(edge_count.items()):
                        logger.debug(f'Writing edge {i + 1}/{total_items}')
                        cp_f.write(f'{edge}:{hit}\n')
                
                last_checkpoint_batch = batch
                last_checkpoint = time_sum
            
            current = min(left, batch_size)
            if num > 0:
                left -= current
            batch_dir = os.path.join(td, f'{batch}')
            os.makedirs(batch_dir)
            
            logger.info(f'Batch {batch} fuzzing {current} seeds')
            start_time = datetime.now()
            try:
                batch_timeout = current * 0.5
                error_count = wrapper(working_dir, generator, batch_dir, current, batch_timeout)
            except subprocess.TimeoutExpired:
                logger.warning(f'Batch {batch} timeout')
            end_time = datetime.now()
            assert error_count == 0
            batch_count = len(os.listdir(batch_dir))
            logger.info(f'Batch {batch} finished with {batch_count} seeds')
            batch += 1
            count += batch_count
            time_sum += (end_time - start_time).total_seconds()
            
            batch_acc += 1 
            if batch_acc >= para_num:
                logger.info('Appending metadata')
                if not race_mode:
                    append_metadata_conc(callback, batch_record, batch_acc, td, para_num)
                logger.info('Getting coverage')
                if not race_mode:
                    cov_module.get_cov_conc(working_dir, td, td, para_num, batch_acc, batch_record, os.path.join(afl_dir, 'afl-showmap'))
                for i in range(batch_acc):
                    batch_dir = os.path.join(td, f'{batch_record + i}')
                    try:
                        shutil.move(batch_dir, os.path.join(out_dir, f'{batch_record + i}'))
                    except:
                        pass
                    if target_name == 'libxml2':
                        logger.info('Remove an extra tmp dir for libxml2')
                        tmp_dir = os.path.join(working_dir, f'{i}-tmp')
                        try:
                            shutil.move(tmp_dir, os.path.join(out_dir, f'{i}-tmp'))
                        except:
                            pass
                batch_acc = 0
                batch_record = batch
        
        if batch_acc > 0:
            logger.info('Appending metadata')
            if not race_mode:
                append_metadata_conc(callback, batch_record, batch_acc, td, para_num)
            logger.info('Getting coverage')
            if not race_mode:
                cov_module.get_cov_conc(working_dir, td, td, para_num, batch_acc, batch_record, os.path.join(afl_dir, 'afl-showmap'))
            for i in range(batch_acc):
                batch_dir = os.path.join(td, f'{batch_record + i}')
                try:
                    shutil.move(batch_dir, os.path.join(out_dir, f'{batch_record + i}'))
                except:
                    pass
                if target_name == 'libxml2':
                    logger.info('Remove an extra tmp dir for libxml2')
                    tmp_dir = os.path.join(working_dir, f'{i}-tmp')
                    try:
                        shutil.move(tmp_dir, os.path.join(out_dir, f'{i}-tmp'))
                    except:
                        pass
            batch_acc = 0
            batch_record = batch
    
        logger.info('Merging coverage files')
        if not race_mode:
            with open(os.path.join(td, 'sum.cov'), 'w') as f:
                edge_count = {}
                start = 0
                if check_point > 0:
                    start = last_checkpoint_batch
                    if last_checkpoint > 0:
                        with open(os.path.join(working_dir, f'cp_{last_checkpoint}.cov'), 'r') as last_cp_f:
                            logger.debug(f'Load checkpoint {last_checkpoint}')
                            for l in last_cp_f:
                                (edge, hit) = l.strip().split(':')
                                edge_count[edge] = int(hit)

                for i in range(start, batch):
                    logger.debug(f'Merging batch {i} / {batch - 1}')
                    with open(os.path.join(td, f'{i}.cov'), 'r') as batch_cov:
                        total_lines = sum(1 for _ in batch_cov)
                        batch_cov.seek(0)
                        for ii, l in enumerate(batch_cov):
                            logger.debug(f'Merging batch {ii + 1}/{total_lines} (in batch {i})')
                            (edge, hit) = l.strip().split(':')
                            if edge in edge_count:
                                edge_count[edge] += int(hit)
                            else:
                                edge_count[edge] = int(hit)
                logger.debug('Writing to sum.cov')
                total_items = len(edge_count)
                for i, (edge, hit) in enumerate(edge_count.items()):
                    logger.debug(f'Writing edge {i + 1}/{total_items}')
                    f.write(f'{edge}:{hit}\n')
            shutil.copy(os.path.join(td, 'sum.cov'), os.path.join(working_dir, 'sum.cov'))
        executor.shutdown(wait=False)
    logger.info('Done')
    stat_file.write(f'{count} test cases in {time_sum} seconds\n')
    sys.path.pop(0)
    
if __name__ == '__main__':
    main()
