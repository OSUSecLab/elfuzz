import tempfile
import subprocess
import random
import os
import os.path
import logging
import concurrent.futures
from typing import Any

logger = logging.getLogger(__file__)

def afl_showmap_cov(showmap_path, prog, input_dir, cov_file, batch_size):
    logger.info(f'Running afl-showmap {input_dir}')
    cmd = [showmap_path, '-q', '-i', input_dir, '-o', cov_file, '-m', 'none', '-C', '--', prog, '@@']
    logger.info(f'showmap_cmd = "{" ".join(cmd)}"')
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={'AFL_QUIET': '1'},
            timeout=batch_size * 0.05
        )
    except subprocess.TimeoutExpired:
        logger.warning(f'afl-showmap timeout')
    with open(cov_file, 'r') as f:
        return set(l.strip() for l in f)
    
def append_metadata(input_dir, tmp_dir, gen_seed_path: str, batch_size):
    cmd = [
        gen_seed_path,
        'xml',
        f'{input_dir}/*'
    ]
    
    os.makedirs(os.path.join(tmp_dir, 'seed', 'xml'))
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=tmp_dir,
            timeout=batch_size * 0.05
        )
    except subprocess.TimeoutExpired:
        logger.warning(f'genXml timeout')

def get_cov(working_dir: str, batch_dir: str, cov_file: str, showmap_path: str, batch_size):
    logger.info(f'Running pre-process {batch_dir}')
    cwd = os.path.dirname(os.path.abspath(__file__))
    
    tmp_dir = os.path.join(os.path.abspath(os.path.join(batch_dir, '..')), f'{os.path.basename(batch_dir)}-tmp')
    os.mkdir(tmp_dir)
    
    append_metadata(batch_dir, tmp_dir, os.path.join(cwd, 'genSeed'), batch_size)
    
    afl_showmap_cov(showmap_path, os.path.join(working_dir, 'xml'), os.path.join(tmp_dir, 'seed', 'xml'), cov_file, batch_size)

m_batch_size = 0

def get_cov_conc(working_dir: str, batch_root: str, cov_file_root: str, total_para_num: int, batch_bundle: int, start_count: int, showmap_path: str = '/usr/local/bin/afl-showmap'):
    global m_batch_size
    logger.info(f'batch_size = {m_batch_size}')
    with concurrent.futures.ProcessPoolExecutor(max_workers=total_para_num) as executor:
        futures: list[concurrent.futures.Future[Any]] = []
        for i in range(batch_bundle):
            batch_dir = os.path.join(batch_root, f'{i+start_count}')
            cov_file = os.path.join(cov_file_root, f'{i+start_count}.cov')
            futures.append(executor.submit(get_cov, working_dir, batch_dir, cov_file, showmap_path, m_batch_size))
        
        count = 0
        for future in futures:
            future.result()
            logger.info(f'Finished {count}/{total_para_num} batch ({start_count + count})')
            count += 1
        executor.shutdown(wait=False)
