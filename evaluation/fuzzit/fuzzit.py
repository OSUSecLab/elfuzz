import logging
from idontwannadoresearch import MailLogger, watch
import click as clk
import subprocess
import os.path
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed, Future

logger = logging.getLogger(__file__)
mailogger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml", chained_logger=logger)
FILE_D = os.path.dirname(__file__)
CVC5_D = os.path.join(FILE_D, os.pardir, 'workdir', 'cvc5')
DICT_D = os.path.join(FILE_D, os.pardir, 'afl_dict', 'cvc5')
ENV = {
    'AFL_MAP_SIZE': '2097152',
    'LD_LIBRARY_PATH': CVC5_D,
    'AFL_TESTCACHE_SIZE': '256',
    'AFL_IGNORE_SEED_PROBLEMS': '1',
    'AFL_CMPLOG_ONLY_NEW': '1',
    'AFL_FAST_CAL': '1',
    'AFL_NO_STARTUP_CALIBRATION': '1'
}

def run(cmd, show_output=False):
    if "AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES" in os.environ:
        ENV["AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES"] = os.environ["AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES"]
    subprocess.run(cmd, env=ENV,
                   stdout=subprocess.DEVNULL if not show_output else sys.stdout, 
                   stderr=subprocess.DEVNULL if not show_output else sys.stderr)

TIME_LIMIT = 5000

@clk.command()
@clk.option('--afl-fuzz', '-a', type=clk.Path(exists=True, dir_okay=False, file_okay=True), required=True, default='/usr/bin/afl-fuzz')
@clk.option('--input-dir', '-i', type=clk.Path(exists=True, file_okay=False, dir_okay=True), required=True)
@clk.option('--output-dir', '-o', type=clk.Path(exists=False, file_okay=False, dir_okay=True), required=False, default=None)
@clk.option('--process-num', '-j', type=int, required=False, default=24)
@clk.option('--resume', is_flag=True, default=False)
@clk.option('--time', '-t', type=int, required=False, default=-1)
@watch(mailogger, report_ok=True)
def main(input_dir, output_dir, afl_fuzz, process_num, resume, time):
    cmd = [
        afl_fuzz, '-t', str(TIME_LIMIT),
    ]
    
    if resume:
        cmd += ['-i', '-', '-o', input_dir]
    else:
        cmd += ['-i', input_dir, '-o', output_dir]
        
    if time > 0:
        cmd += ['-V', str(time)]
    
    dict_files = [os.path.join(DICT_D, f) for f in os.listdir(DICT_D)]
    dict_options = []
    for f in dict_files:
        dict_options += ['-x', f]
    cmd += dict_options
        
    bin_cmd = ['--', os.path.join(CVC5_D, 'cvc5'), '@@']
    
    with ProcessPoolExecutor(max_workers=process_num) as executor:
        futures = []
        for i in range(process_num):
            f = executor.submit(run, cmd + ['-M' if i == 0 else '-S', f'fuzzer{i}'] + bin_cmd, i == 0)
            futures.append(f)
        mailogger.log(f'FuzzIt started with {process_num} processes')
        count = 0
        for f in as_completed(futures):
            count += 1
            logger.info(f'fuzzer{count} finished')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
