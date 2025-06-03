import os
import subprocess
import sys
from tqdm import tqdm

PWD = os.path.realpath(os.path.dirname(__file__))

cov_files = [
    os.path.join(PWD, 'cvc5_zest', f) for f in os.listdir(os.path.join(PWD, 'cvc5_zest')) if f.endswith('.cov') and f.startswith('cp_')
]

def extract_time(file_name) -> float:
    file_stem: str = os.path.basename(file_name)
    time_str = file_stem.removeprefix('cp_').removesuffix('.cov')
    return float(time_str)

cov_files.sort(key=extract_time)

bin = os.path.join(PWD, 'cvc5_zest', 'cvc5')
for idx in tqdm(range(10)):
    seed_dir = os.path.join(PWD, 'cvc5_zest', 'out', str(idx))
    cmd = [
        'afl-showmap', '-C', '-i', seed_dir, '-o', os.path.join(PWD, 'cvc5_zest', f'zest_cov_{idx}'), '--', bin, '@@'
    ]
    subprocess.run(cmd, check=False, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                   env={'AFL_QUIET': '1', 'AFL_MAP_SIZE': '2097152', 'LD_LIBRARY_PATH': os.path.join(PWD, 'cvc5_zest')})
