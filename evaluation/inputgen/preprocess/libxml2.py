import click as clk
import os.path
import subprocess
import tempfile
import concurrent.futures
import shutil
import tqdm

import logging

logger = logging.getLogger(__name__)

def process_batch(gen_xml: str, input_dir: str, output_dir: str):
    cmd = [
        gen_xml,
        'xml',
        f'{input_dir}/*'
    ]
    
    subprocess.run(cmd, check=True, cwd=output_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

BATCH_SIZE = 1000

@clk.command()
@clk.option('--input', '-i', type=clk.Path(exists=True), required=True)
@clk.option('--output', '-o', type=clk.Path(), required=True)
@clk.option('--para', '-j', type=int, default=20, required=False)
def main(input, output, para):
    cwd = os.path.dirname(__file__)
    
    all_files = os.listdir(input)
    gen_seed = os.path.join(cwd, '..', '..', 'binary', 'libxml2', 'genSeed')
    
    batch_num = len(all_files) // BATCH_SIZE
    residue = len(all_files) % BATCH_SIZE
    
    batches = []
    
    for i in range(batch_num):
        batches.append(all_files[i * BATCH_SIZE:(i + 1) * BATCH_SIZE])
    
    if residue != 0:
        batches.append(all_files[batch_num * BATCH_SIZE:])
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=para) as executor, \
         tempfile.TemporaryDirectory() as temp_dir:
        progress = tqdm.tqdm(total=len(all_files))
        fts = []
        for i, batch in enumerate(batches):
            os.makedirs(os.path.join(temp_dir, f'batch_{i}_in'), exist_ok=True)
            os.makedirs(os.path.join(temp_dir, f'batch_{i}_out', 'seed', 'xml'), exist_ok=True)
            
            for file in batch:
                shutil.copy2(os.path.join(input, file), os.path.join(temp_dir, f'batch_{i}_in', file))
            f = executor.submit(process_batch, gen_seed, os.path.join(temp_dir, f'batch_{i}_in'), os.path.join(temp_dir, f'batch_{i}_out'))
            f.add_done_callback(lambda x: progress.update(len(batch)))
            fts.append(f)
        for i, f in enumerate(concurrent.futures.as_completed(fts)):
            f.result()
            logger.info(f'Batch {i} done')
        progress.close()
        for i in tqdm.tqdm(range(len(batches))):
            for file in os.listdir(os.path.join(temp_dir, f'batch_{i}_out', 'seed', 'xml')):
                shutil.copy2(os.path.join(temp_dir, f'batch_{i}_out', 'seed', 'xml', file), os.path.join(output, file))

if __name__ == '__main__':
    main()
