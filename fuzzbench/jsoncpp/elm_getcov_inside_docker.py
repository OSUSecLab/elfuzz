import tempfile
import subprocess
import click
from concurrent.futures import ThreadPoolExecutor, as_completed
import glob
import os
from tqdm import tqdm
import json
import random

# ./afl-showmap -q -i {} -o {/}.cov -C -- ./gifread @@
def afl_showmap_cov(showmap_path, prog, input_dir):
    with tempfile.NamedTemporaryFile() as f:
        cov_file = f.name
        cmd = [showmap_path, '-q', '-i', input_dir, '-o', cov_file, '-m', 'none', '-C', '--', prog, '@@']
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={'AFL_QUIET': '1'},
        )
        with open(cov_file, 'r') as f:
            return set(l.strip() for l in f)

def afl_fuzz_cov(fuzz_path, showmap_path, prog, input_dir, timeout):
    with tempfile.TemporaryDirectory() as d:
        cmd = [fuzz_path, '-d', '-i', input_dir, '-o', d, '-V', str(timeout), '--', prog, '@@']
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={'AFL_QUIET': '1', 'AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES': '1', 'AFL_SKIP_CPUFREQ': '1'}
        )
        return afl_showmap_cov(showmap_path, prog, f'{d}/default/queue')
        
@click.command()
@click.option('--afl-path', 'afl_path', required=False, type=str, default='/src/aflplusplus')
@click.option('--prog', required=True, type=str)
@click.option('--input', required=True, type=str)
@click.option('--output', required=True, type=str)
@click.option('-j', 'parallel_num', type=int, required=False, default=64)
@click.option('--real-feedback', 'real_feedback', type=bool, default=False)
@click.option('--afl-timeout', 'afl_timeout', type=int, default=-1)
def main(prog: str, input: str, afl_path: str, output: str, parallel_num: int, real_feedback: bool, afl_timeout: int):
    if real_feedback:
        print('Using real feedbacks', flush=True)
    
    combined_cov = {}
    with ThreadPoolExecutor(max_workers=parallel_num) as executor:
        worklist = []
        for model in glob.glob(os.path.join(input, '*')):
            for generator in glob.glob(os.path.join(model, '*')):
                    worklist.append((
                        os.path.basename(model),
                        os.path.basename(generator),
                        generator,
                    ))
        futures = {}
        progress = tqdm(total=len(worklist), desc='Coverage')
        for model, generator, gendir in worklist:
            input_files = os.listdir(gendir)
            
            for input_file in input_files:
                with open(f'{gendir}/{input_file}', 'rb') as tmpf:
                    b = tmpf.read()
                with open(f'{gendir}/{input_file}', 'wb') as tmpf:
                    tmpf.write(random.randint(0, 0xFFFFFFFF).to_bytes(4, 'little', signed=False) + b) # Use random control flags of the fuzzer
            
            if not real_feedback:
                future = executor.submit(afl_showmap_cov, f'{afl_path}/afl-showmap', prog, gendir)
            else:
                future = executor.submit(afl_fuzz_cov, f'{afl_path}/afl-fuzz', f'{afl_path}/afl-showmap', prog, gendir, afl_timeout)
            futures[future] = (model, generator, gendir)
            future.add_done_callback(lambda _: progress.update())
        for future in as_completed(futures):
            model, generator, gendir = futures[future]
            cov = future.result()
            combined_cov[(model, generator)] = cov
        progress.close()
    cov_dict = {}
    for (model, generator), cov in combined_cov.items():
        if model not in cov_dict:
            cov_dict[model] = {}
        cov_dict[model][generator] = list(cov)
    with open(output, 'w') as f:
        json.dump(cov_dict, f)
        
if __name__ == '__main__':
    main()
