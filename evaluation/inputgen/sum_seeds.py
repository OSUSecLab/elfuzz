from idontwannadoresearch import MailLogger, watch
from idontwannadoresearch.mapreduce import project, segment, mapping, accumulate
import logging

logger = logging.getLogger(__file__)
mailogger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml", chained_logger=logger)


BENCHMARKS = [
    'libxml2',
    're2',
    'sqlite3',
    'cpython3',
    'cvc5',
    'librsvg',
    'jsoncpp',
]

FUZZERS = {
    'elm': '',
    'grmr': '_grammarinator',
    'isla': '_isla',
    'islearn': '_islearn',
    'alt': '_alt'
}

EXCLUDES = [('re2', 'islearn'), ('jsoncpp', 'islearn')]

import itertools
import os
import os.path
import shutil
from tqdm import tqdm
import click as clk

@clk.command()
@clk.option('--root-dir', '-i', type=str, required=True)
@clk.option('--out-dir', '-o', type=str, required=True)
@watch(mailogger, report_ok=True)
def main(root_dir: str, out_dir):
    for benchmark, (fuzzer, suffix) in itertools.product(BENCHMARKS, FUZZERS.items()):
        logger.info(f'{benchmark}_{fuzzer}')
        seed_dir = os.path.join(root_dir, f'{benchmark}{suffix}', 'out')
        
        if (benchmark, fuzzer) in EXCLUDES:
            continue
        if not os.path.exists(seed_dir):
            mailogger.log(f'{benchmark}_{fuzzer} not found')
            continue
        
        __out_dir = os.path.join(out_dir, f'{benchmark}_{fuzzer}', 'seeds')
        os.makedirs(__out_dir, exist_ok=True)
        
        subdirs = [d for d in os.listdir(seed_dir) if d.isdigit()]
        
        seg_num = len(subdirs) // 1

        def move(dirs: list[str]) -> None:
            for d in dirs:
                dir_name = os.path.basename(d)
                for f in os.listdir(os.path.join(seed_dir, d)):
                    shutil.copy(os.path.join(seed_dir, d, f), os.path.join(__out_dir, f'{dir_name}_{f}'))
            
        with tqdm(total=len(subdirs)) as pbar:
            (project(subdirs) >>
                segment(seg_num) >>
                mapping(move, para_num=20, callback=lambda args, _future: pbar.update(len(args))) >> # type: ignore
                accumulate(lambda x: x)
            ) # type: ignore
        mailogger.log(f'{benchmark}_{fuzzer} done')
        
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()