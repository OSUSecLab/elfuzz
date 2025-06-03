import os
import os.path
import subprocess
import click as clk
from idontwannadoresearch.mapreduce import project, segment, accumulate, mapping
import tempfile
import shutil
from tqdm import tqdm
import random

CWD = os.path.dirname(os.path.abspath(__file__))
BIANRY_DIR = os.path.join(CWD, os.path.pardir, os.path.pardir, 'binary', 'sqlite3')
COV_BIN = os.path.join(BIANRY_DIR, 'ossfuzz')

@clk.command()
@clk.option('--parallel', '-j', type=int, default=1)
@clk.option('--input', '-i', type=clk.Path(exists=True))
@clk.option('--output', '-o', type=clk.Path(exists=False))
def main(parallel, input, output):
    input_files = []
    for f in os.listdir(input):
        input_files.append(os.path.join(input, f))
    BATCH_SIZE = 20
    batches = []
    # pbar = tqdm(total=len(input_files))
    with tempfile.TemporaryDirectory() as tmpdir, \
         tqdm(total=len(input_files)) as pbar:
        def mapping_fun(batch: list[str]) -> list[str]:
            while True:
                rand_no = random.randint(0, 100000000)
                if not os.path.exists(os.path.join(tmpdir, str(rand_no))):
                    break
            tmp_in = os.path.join(tmpdir, str(rand_no), 'in')
            tmp_out = os.path.join(tmpdir, str(rand_no), 'out')
            os.makedirs(tmp_in)
            os.makedirs(tmp_out)
            for file in batch:
                shutil.copy(file, tmp_in)
            cmd = [
                'afl-showmap', '-i', tmp_in, '-o', tmp_out, '--', COV_BIN, '@@'
            ]
            for f in batch:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return [os.path.join(tmp_out, f) for f in os.listdir(tmp_out)]
        def accumulate_fun(file_batches: list[list[str]]):
            for batch in file_batches:
                for f in batch:
                    shutil.copy(f, output)

        (project(input_files) >>
         segment(len(input_files) // BATCH_SIZE) >>
         mapping(mapping_fun, callback=lambda input, _future: pbar.update(len(input)), para_num=parallel) >> # type: ignore
         accumulate(accumulate_fun)
        ) # type: ignore

if __name__ == '__main__':
    main()