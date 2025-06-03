import os
import os.path
import subprocess
import click as clk
import tempfile
from idontwannadoresearch.mapreduce import project, segment, accumulate, mapping
import re
from tqdm import tqdm
import json
import sys

CWD = os.path.dirname(os.path.abspath(__file__))
BIANRY_DIR = os.path.join(CWD, os.path.pardir, os.path.pardir, 'binary', 'sqlite3_cov')
COV_BIN = os.path.join(BIANRY_DIR, 'ossfuzz')
GCOV = os.path.join(BIANRY_DIR, 'gcov-9.4')
COV_SRC = os.path.join(BIANRY_DIR, 'sqlite3_src.tar.xz')
BLD_DIR_MAP_FILE = os.path.join(BIANRY_DIR, 'bld_src_map')
TARBALL_ROOT = 'src/sqlite3'

def clear_gcda(root):
    for root, dirs, files in os.walk(root):
        for f in files:
            if f.endswith('.gcda'):
                os.remove(os.path.join(root, f))

def process_one_batch(inputs: list[str]) -> dict[str, int]:
    pattern2 = re.compile(r'Lines executed:(\d+\.\d+)% of \d+')
    pattern1 = re.compile(r"File '(.*)'")
    result = {}
    with tempfile.TemporaryDirectory() as tmp_dir:
        extract_cmd = [
            'tar', '-xJf', COV_SRC, '-C', tmp_dir
        ]
        subprocess.run(extract_cmd, check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        
        for input in inputs:
            clear_gcda(tmp_dir)
            run_cmd = [
                COV_BIN, input
            ]
            to_inspects = []
            subprocess.run(run_cmd, check=True, cwd=tmp_dir, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, env={'GCOV_PREFIX': tmp_dir})
            for root, dirs, files in os.walk(tmp_dir):
                for f in files:
                    if f.endswith('.gcda'):
                        to_inspects.append(os.path.join(root, f))
            for to_inspect in to_inspects:
                gcov_cmd = [
                    GCOV, os.path.join(TARBALL_ROOT, to_inspect)
                ]
                
                r = subprocess.run(gcov_cmd, capture_output=True, text=True,
                                    env={'GCOV_PREFIX': tmp_dir}, check=True, cwd=tmp_dir)
                lines = r.stdout.split('\n')
                current_file = None
                for l in lines:
                    m1 = pattern1.match(l)
                    m2 = pattern2.match(l)
                    if m1:
                        current_file = m1.group(1)
                    elif m2:
                        assert current_file is not None
                        if not current_file.startswith('/' + TARBALL_ROOT):
                            continue
                        cov = float(m2.group(1))
                        if cov != 0.0:
                            if current_file.endswith('vacuum.c'):
                                print(f'vucuum.c: {input}')
                            elif current_file.endswith('ctime.c'):
                                print(f'ctime.c: {input}')
                            elif current_file.endswith('vdbesort.c'):
                                print(f'vdbesort.c: {input}')
                            if current_file not in result:
                                result[current_file] = 0
                            result[current_file] += 1

    return result

def combine_batches(results: list[dict[str, int]]) -> dict[str, int]:
    result = {}
    for r in results:
        for k, v in r.items():
            if k not in result:
                result[k] = 0
            result[k] += v
    return result

@clk.command()
@clk.option('--parallel', '-j', type=int, default=1)
@clk.option('--input', '-i', type=clk.Path(exists=True))
@clk.option('--output', '-o', type=str)
@clk.option('--selected', '-s', type=clk.Path(exists=True), default=None)
def main(parallel, input, output, selected):
    bld_dir_map = {}
    skip = set()

    with open(BLD_DIR_MAP_FILE, 'r') as f:
        for line in f:
            src, redirect = line.strip().split('->')
            src = src.strip()
            redirect = redirect.strip()
            if redirect == '!':
                skip.add(src)
            else:
                bld_dir_map[src] = redirect

    BATCH_SIZE = 20
    if selected is not None:
        input_files = []
        with clk.open_file(selected, 'r') as f:
            for l in f:
                input_files.append(os.path.join(os.path.abspath(input), l.strip()))
    else:
        input_files = [
            os.path.join(os.path.abspath(input), f) for f in os.listdir(input)
        ]
    
    with tqdm(total=len(input_files)) as pbar:
        results = (
            project(input_files) >>
            segment(len(input_files) // BATCH_SIZE) >>
            mapping(process_one_batch, para_num=parallel, callback=lambda inputs, _future: pbar.update(len(inputs))) >> # type: ignore
            accumulate(combine_batches)
        ) # type: ignore
    with clk.open_file(output, 'w') as f:
        json.dump(results, f, indent=4)

if __name__ == '__main__':
    main()
