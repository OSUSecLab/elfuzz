#!/usr/bin/env python3

import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess
import tempfile
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import glob
import os

AFL_DIR = '/usr/bin'
# ./afl-showmap -q -i {} -o {/}.cov -C -- ./gifread @@
def afl_cov(showmap_path, prog, input_dir):
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

def make_parser():
    parser = argparse.ArgumentParser(description="Get coverage for generated inputs")
    parser.add_argument('gendir', help='Base directory for generated inputs, structure: gendir/[model]/[generator]/[files]')
    parser.add_argument('-O', '--output', type=str, default='output.json',
                        help='Output file where coverage will be written')
    parser.add_argument('-j', '--jobs', type=int, default=64,
                        help='Number of parallel jobs')
    parser.add_argument("--afl_dir", type=Path,
                        help="Path to AFL++ directory (for afl-showmap)",
                        default=Path(AFL_DIR))
    parser.add_argument('--real_feedback', default=False, action="store_true")
    parser.add_argument('--afl_timeout', type=int)
    return parser

def init_parser(elm):
    pass

def main():
    from idontwannadoresearch.txdm import txdm
    from elmconfig import ELMFuzzConfig
    parser = make_parser()
    config = ELMFuzzConfig(parents={'getcov': parser})
    args = config.parse_args()
    showmap = args.afl_dir / 'afl-showmap'
    if not showmap.exists():
        config.parser.error(f'afl-showmap not found at {showmap}')
    if not args.target.covbin:
        config.parser.error('Coverage binary not specified')
    covbin = args.target.covbin.expanduser()
    if not covbin:
        config.parser.error(f'Coverage binary not found at {args.target.covbin}')
    combined_cov = {}
    with ThreadPoolExecutor(max_workers=64) as executor:
        worklist = []
        for model in glob.glob(os.path.join(args.gendir, '*')):
            for generator in glob.glob(os.path.join(model, '*')):
                    worklist.append((
                        os.path.basename(model),
                        os.path.basename(generator),
                        generator,
                    ))
        futures = {}
        progress = (tqdm(total=len(worklist), desc='Coverage')
                    if not ON_NSF_ACCESS else txdm(len(worklist), desc='Coverage'))
        for model, generator, gendir in worklist:
            future = executor.submit(afl_cov, showmap, covbin, gendir)
            futures[future] = (model, generator, gendir)
            future.add_done_callback(lambda _: progress.update())
        for future in as_completed(futures):
            model, generator, gendir = futures[future]
            cov = future.result()
            combined_cov[(model, generator)] = cov
        progress.close()
    # for (model, generator), cov in combined_cov.items():
    #     print(f'{model:>20} {generator} {len(cov)}')
    cov_dict = {}
    for (model, generator), cov in combined_cov.items():
        if model not in cov_dict:
            cov_dict[model] = {}
        cov_dict[model][generator] = list(cov)
    with open(args.output, 'w') as f:
        json.dump(cov_dict, f)
        
ON_NSF_ACCESS = False

def on_nsf_access() -> dict[str, str] | None:
    if not 'ACCESS_INFO' in os.environ:
        return None
    endpoint = os.environ['ACCESS_INFO']
    sif_root = os.environ['SIF_ROOT']
    return {
        'endpoint': endpoint,
        'sif_root': sif_root,
    }

if  __name__ == '__main__':
    ON_NSF_ACCESS = on_nsf_access() is not None
    main()
