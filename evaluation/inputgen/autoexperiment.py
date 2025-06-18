import subprocess
import shutil
import os
import os.path
import sys
from datetime import datetime
from idontwannadoresearch import MailLogger, watch
import click as clk

mailogger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml")

CMD = [
    'python',
    'run_afl.py',
    '-t', '3600',
    '-s', '-1',
    '-o', 'tmp/savepoints',
]

CWD = os.path.dirname(os.path.abspath(__file__))

ROOT = os.path.join(CWD, os.pardir, os.pardir)

FUZZERS = ['elm', 'alt', 'grmr', 'isla', 'islearn']

@clk.command()
@clk.option('--repeat', '--indentifier', '-r', type=int, default=1)
@watch(mailogger, report_ok=True)
def main(repeat):
    for fuzzer in FUZZERS:
        experiment_file = f'tmp/experiments-{fuzzer}'
        with open('experiments', 'r') as f:
            contents = f.read()
        with open(experiment_file, 'w') as f:
            f.write(contents
                    .replace(r'%FUZZER%', fuzzer)
                    .replace(r'%ROOT%', ROOT)
                    .replace(r'%REPEAT%', str(repeat))
            )
        with open(experiment_file, 'r') as f:
            for line in f:
                _, out, _, _ = line.split('|')
                out = out.strip()
                if os.path.exists(out):
                    shutil.rmtree(out)
                os.makedirs(out)
        cmd = CMD + [experiment_file]
        subprocess.run(cmd, check=True, stdout=sys.stdout, stderr=sys.stderr)
        # current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        mailogger.log(f'{fuzzer} experiments finished')
if __name__ == '__main__':
    main()