import subprocess
import shutil
import os
import os.path
import sys
import smtplib
from email.message import EmailMessage
from datetime import datetime
from idontwannadoresearch import MailLogger, watch
import click as clk
import logging

logger = logging.getLogger(__file__)
mailogger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml", logger)

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
@clk.option('--repeat', '-n', type=int, default=1, required=False)
@watch(mailogger, report_ok=True)
def main(repeat):
    for i in range(1, repeat + 1):
        for fuzzer in FUZZERS:
            experiment_file = f'tmp/experiments-{fuzzer}'
            with open('experiments', 'r') as f:
                contents = f.read()
            with open(experiment_file, 'w') as f:
                f.write(contents
                        .replace(r'%FUZZER%', fuzzer)
                        .replace(r'%ROOT%', ROOT)
                        .replace(r'%REPEAT%', str(i))
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
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            mailogger.log(f'Sub-experiment R{i}-{fuzzer} completed at {current_time}')
if __name__ == '__main__':
    main()
