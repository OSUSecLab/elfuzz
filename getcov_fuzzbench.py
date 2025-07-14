import click
import tempfile
import shutil
import sys
import os.path
from util import *
import logging
from idontwannadoresearch import MailLogger, watch

logger = logging.getLogger(__file__)
mailogger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml", chained_logger=logger)

def on_nsf_access() -> dict[str, str] | None:
    if not 'ACCESS_INFO' in os.environ:
        return None
    endpoint = os.environ['ACCESS_INFO']
    sif_root = os.environ['SIF_ROOT']
    return {
        'endpoint': endpoint,
        'sif_root': sif_root,
    }

@click.command()
@click.option('--image', type=str, required=True)
@click.option('--input', type=str, required=True)
@click.option('--persist/--no-persist', type=bool, default=False)
@click.option('--covfile', type=str, default='./cov.json')
@click.option('-j', 'parallel_num', type=int, default=64, required=False)
@watch(mailogger)
def main(image: str, input: str, persist: bool, covfile: str, parallel_num: int):
    covbin = get_config('target.covbin')
    if isinstance(covbin, list):
        covbin_str = ' '.join(covbin)
    else:
        covbin_str = covbin
    access_info = on_nsf_access()
    real_feedback = get_config('cli.getcov.real_feedback') == 'true'
    afl_timeout = int(get_config('cli.getcov.afl_timeout'))
    
    cwd = os.path.dirname(os.path.abspath(__file__))
    if access_info is not None:
        prefix = os.path.join(cwd, 'tmp', 'fuzzdata') + '/'
    elif bool(os.environ.get('REPROUDCE_MODE', 'false')):
        prefix = '/tmp/host/fuzzdata/'
    else:
        prefix = '/tmp/fuzzdata/'
    if not os.path.exists(prefix):
        os.makedirs(prefix)
    
    with tempfile.TemporaryDirectory(prefix=prefix) as tmpdir:
        target_dir = os.path.join(tmpdir, 'input')
        shutil.move(input, target_dir)
        if access_info is None:
            cmd = [
                'docker',
                'run'
            ]
            if not persist:
                cmd.append('--rm')
            cmd.extend([
                '-v', f'{tmpdir}:/tmp',
                image,
                f'/usr/bin/bash', '-c', f'python3 /src/elm_getcov_inside_docker.py --input /tmp/input --output /tmp/cov -j {parallel_num} --prog="{covbin_str}" --real-feedback {real_feedback} --afl-timeout={afl_timeout}'
            ])
        else:
            cmd = [
                'apptainer', 'exec',
                '--cleanenv',
                '--bind', f'{tmpdir}:/tmp:rw',
                os.path.join(access_info['sif_root'], image),
                '/usr/bin/bash', '-c', f'python3 /src/elm_getcov_inside_docker.py --input /tmp/input --output /tmp/cov -j {parallel_num} --prog="{covbin_str}" --real-feedback {real_feedback} --afl-timeout={afl_timeout}'
            ]
        print(' '.join(cmd))
        subprocess.run(cmd, check=True, stdout=sys.stdout, stderr=sys.stderr)
        shutil.copy(f'{tmpdir}/cov', covfile)
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
