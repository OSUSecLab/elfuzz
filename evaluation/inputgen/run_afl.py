from datetime import datetime, timedelta
import time
import logging
import tempfile
import shutil
import subprocess
import os
import os.path
import click as clk
import concurrent.futures
from idontwannadoresearch import MailLogger, diagnose

logger = logging.getLogger(__name__)
mailogger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml")

def watch_dog(total_time: int, 
              savepoint_interval: int,
              watch_on: list[str],
              startup_delay: list[int],
              store_dir: str) -> list[str]:
    if total_time <= 0 or savepoint_interval <= 0:
        raise ValueError('savepoint_interval must be non-negative')
    
    assert total_time >= savepoint_interval
    
    if savepoint_interval in range(0, 1):
       sleep_time = 0 
    else:
        sleep_time = 1
    
    abs_start_time = datetime.now()
    start_time = [abs_start_time + timedelta(0, s) for s in startup_delay]
    status = [0 for _ in startup_delay]
    last_savepoint = [s for s in start_time]
    savepoints = []
    sp_counters = [0 for _ in startup_delay]
    
    logger.info(f'Starting watch dog with sleep time {sleep_time}')
    logger.info(f'Start time: {abs_start_time}')
    time_elapsed = 0
    while any(s != 2 for s in status):
        time.sleep(sleep_time)
        logger.debug('Checking savepoint')
        current_time = datetime.now()
        for i, (watchdir, st) in enumerate(zip(watch_on, start_time)):
            if current_time < st:
                continue
            if status[i] == 0:
                logger.info(f'{watchdir} started after {startup_delay[i]}s delay')
                status[i] = 1
            if status[i] == 2:
                logger.debug(f'{watchdir} already finished, skip')
                continue
            
            time_elapsed = (current_time - st).seconds
            if time_elapsed >= total_time:
                sp_name = f'savepoint_e_{time_elapsed}'
                assert status[i] == 1
                logger.info(f'{watchdir} finished total time {total_time}')
                status[i] = 2
            elif (current_time - last_savepoint[i]).seconds >= savepoint_interval:
                last_savepoint[i] = current_time
                sp_counters[i] += 1
                sp_name = f'savepoint_{sp_counters[i]}_{time_elapsed}'
            else:
                continue
            logger.info(f'Creating savepoint {sp_name}')
            stem = os.path.basename(watchdir)
            dest = os.path.join(store_dir, stem)
            if not os.path.exists(dest):
                os.makedirs(dest)
            logger.info(f'Copying {watchdir} to {os.path.join(dest, sp_name)}')
            try:
                shutil.copytree(watchdir, os.path.join(dest, sp_name))
            except:
                pass
            savepoints.append(os.path.join(dest, sp_name))
            logger.info(f'Copied {watchdir} to {os.path.join(dest, sp_name)}')
    logger.info('Watch dog exited')
    return savepoints

def run_afl(cmd: str, env_vars: dict[str, str]) -> None:
    for k, v in env_vars.items():
        os.environ[k] = v
    logger.info(f'Running {cmd} with {env_vars}')
    os.system(cmd + ' > /dev/null')
    logger.info(f'{cmd} completed')

@clk.command()
@clk.option('--total-time', '-t', type=int, required=True)
@clk.option('--savepoint-interval', '-s', type=int, required=True)
@clk.argument('experiment-desc', type=clk.File('r'), required=True)
@clk.option('--output', '-o', type=clk.Path(exists=True, file_okay=False, dir_okay=True), required=True)
def main(total_time, savepoint_interval, experiment_desc, output):
    logging.basicConfig(level=logging.INFO)
    
    cwd = os.path.dirname(os.path.realpath(__file__))
    project_root = os.path.abspath(os.path.join(cwd, os.pardir, os.pardir))
    
    experiments = []
    for line in experiment_desc:
        if '#' in line:
            line, _ = line.split('#')
        if not line.strip():
            continue
        cmd, afl_dir, env_file, delay = [t.strip() for t in line.strip().split('|')]
        afl_dir = afl_dir.replace('%ROOT%', project_root)
        if not os.path.exists(afl_dir):
            os.makedirs(afl_dir)
        cmd = cmd.replace(r'%out', afl_dir).replace(r'%time', str(total_time)).replace('%ROOT%', project_root)
        env_vars = {}
        if env_file:
            with open(env_file.replace('%ROOT%', project_root), 'r') as f:
                for line in f:
                    k, v = line.strip().split('=')
                    env_vars[k.strip()] = v.strip().replace('%ROOT%', project_root)
        experiments.append((cmd, afl_dir, env_vars, 0 if not delay.strip() else int(delay.strip())))
    def notify(future: concurrent.futures.Future[None]):
        if future.exception():
            mailogger.log(f'Error: {future.exception()}\n---\nDiagnostic: {diagnose()}')
        else:
            mailogger.log(f'{future.result()}')
    with concurrent.futures.ProcessPoolExecutor(len(experiments) + 5) as executor:
        futures = []
        watch_on = []
        startup_delay = []
        for cmd, afl_dir, env_vars, delay in experiments:
            f = executor.submit(run_afl, cmd, env_vars)
            f.add_done_callback(notify) 
            futures.append(f)
            watch_on.append(afl_dir)
            startup_delay.append(delay)
        if savepoint_interval > 0:
            futures.append(executor.submit(watch_dog, total_time, savepoint_interval, watch_on, startup_delay, output))
        for f in concurrent.futures.as_completed(futures):
            f.result()
if __name__ == '__main__':
    main()
