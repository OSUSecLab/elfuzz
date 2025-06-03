import tempfile
import subprocess
import random
import os
import os.path
import logging
import concurrent.futures
from typing import Any

logger = logging.getLogger(__file__)

# os.environ['AFL_QUIET'] = '1'
os.environ['AFL_MAP_SIZE'] = '2097152'
os.environ['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = '1'
os.environ['AFL_SKIP_CPUFREQ'] = '1'

# ./afl-showmap -q -i {} -o {/}.cov -C -- ./gifread @@
def afl_showmap_cov(showmap_path, prog, input_dir, cov_file):
    cmd = showmap_path + ['-q', '-i', input_dir, '-o', cov_file, '-m', 'none', '-C', '--', prog]
    os.system(
        ' '.join(cmd),
    )

def get_cov(working_dir: str, batch_dir: str, cov_file: str, showmap_path):
    logger.info(f'Running pre-process {batch_dir}')
    afl_showmap_cov(showmap_path, os.path.join(working_dir, 'render_document_patched'), batch_dir, cov_file)

def get_cov_conc(working_dir: str, batch_root: str, cov_file_root: str, total_para_num: int, batch_bundle: int, start_count: int, _useless):
    with concurrent.futures.ProcessPoolExecutor(max_workers=total_para_num) as executor:
        futures: list[concurrent.futures.Future[Any]] = []
        for i in range(batch_bundle):
            batch_dir = os.path.join(batch_root, f'{i+start_count}')
            cov_file = os.path.join(cov_file_root, f'{i+start_count}.cov')
            futures.append(executor.submit(get_cov, working_dir, batch_dir, cov_file, ['cargo', 'afl', 'showmap']))
        
        count = 0
        for future in futures:
            future.result()
            logger.info(f'Finished {count}/{total_para_num} batch ({start_count + count})')
            count += 1
        executor.shutdown(wait=False)
