import subprocess
import click as clk
import os.path
import tempfile
import os
import concurrent.futures
import shutil
import tqdm
import logging
import sys

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000

def process_batch(afl_cmin: str, input: str, output: str, binary: str, envs: dict[str, str], use_stdin: bool) -> int:
    cmd = [
        afl_cmin,
        '-i', input,
        '-o', output,
        '-A',
        '--', binary, '@@' if not use_stdin else ''
    ]
    for k, v in envs.items():
        os.environ[k] = v
    os.system(' '.join(cmd) + ' > /dev/null 2>&1')
    return len(os.listdir(output))
        
class MyTmpDir(tempfile.TemporaryDirectory):
    def __init__(self) -> None:
        super().__init__(ignore_cleanup_errors=True)
        self._rmtree = shutil.rmtree

@clk.command()
@clk.option('--afl-cmin', '-a', type=str, required=False, default='afl-cmin')
@clk.option('--use-stdin', '-s', is_flag=True, default=False)
@clk.option('--input', '-i', type=clk.Path(exists=True), required=True)
@clk.option('--output', '-o', type=clk.Path(), required=True)
@clk.option('--para', '-j', type=int, default=20, required=False)
@clk.option('--binary', '-b', type=clk.Path(exists=True), required=True)
@clk.option('--env', '-e', type=clk.Path(exists=True), required=False, default=None)
@clk.option('--one-pass', '-1', is_flag=True, default=False)
def main(input, output, para, binary, env, one_pass, afl_cmin, use_stdin):
    logging.basicConfig(level=logging.INFO)

    cwd = os.path.dirname(os.path.realpath(__file__))
    project_root = os.path.abspath(os.path.join(cwd, os.pardir, os.pardir))
    
    envs = {}
    if env is not None:
        with open(env, 'r') as f:
            for line in f:
                k, v = line.strip().split('=')
                envs[k.strip()] = v.strip().replace('%ROOT%', project_root)
    
    all_files = os.listdir(input)
    batch_num = len(all_files) // BATCH_SIZE
    residue = len(all_files) % BATCH_SIZE
    batches = []
    for i in range(batch_num):
        batches.append(all_files[i * BATCH_SIZE:(i + 1) * BATCH_SIZE])
    if residue != 0:
        batches.append(all_files[batch_num * BATCH_SIZE:])
    with concurrent.futures.ThreadPoolExecutor(max_workers=para) as executor, \
         MyTmpDir() as temp_dir:
        after_min = 0
        progress = tqdm.tqdm(total=len(all_files))
        fts = []
        for i, batch in enumerate(batches):
            os.makedirs(os.path.join(temp_dir, f'batch_{i}_in'), exist_ok=True)
            os.makedirs(os.path.join(temp_dir, f'batch_{i}_out'), exist_ok=True)
            for file in batch:
                shutil.copy2(os.path.join(input, file), os.path.join(temp_dir, f'batch_{i}_in', file))
            f = executor.submit(process_batch, 
                                afl_cmin, 
                                os.path.join(temp_dir, f'batch_{i}_in'), 
                                os.path.join(temp_dir, f'batch_{i}_out'), 
                                binary, envs, use_stdin)
            f.add_done_callback(lambda x: progress.update(len(batch)))
            fts.append(f)
        for i, f in enumerate(concurrent.futures.as_completed(fts)):
            after_min += f.result()
            logger.debug(f'Batch {i} done')
        progress.close()
        logger.info(f'After cmin round 1: {after_min} files')
        double_cmin = os.path.join(temp_dir, 'cmined')
        os.mkdir(double_cmin)
        for i in range(len(batches)):
            for f in os.listdir(os.path.join(temp_dir, f'batch_{i}_out')):
                shutil.copy2(os.path.join(temp_dir, f'batch_{i}_out', f), double_cmin)
                logger.debug(f'File {f} copied to {double_cmin}')
        if not one_pass:
            cmd = [
                'afl-cmin',
                '-i', double_cmin,
                '-o', output,
                '-A',
                '--', binary, '@@'
            ]
            for k, v in envs.items():
                os.environ[k] = v
            os.system(' '.join(cmd))
            final_num = len(os.listdir(output))
            
            logger.info(f'After cmin round 2: {final_num} files')
        else:
            files = os.listdir(double_cmin)
            for f in files:
                shutil.copy2(os.path.join(double_cmin, f), output)

if __name__ == '__main__':
    main()
