import os
import sys
import subprocess
import time
import copy
from datetime import datetime, timedelta

import logging

logger = logging.getLogger(__file__)

def rebuild_phasar():
    build_cmd = ['cmake', '--build', '/phasar/build']
    install_cmd = ['cmake', '-DCMAKE_INSTALL_PREFIX=/usr/local/phasar', '-P', '/phasar/build/cmake_install.cmake']

    subprocess.run(build_cmd, stdout=sys.stdout, stderr=sys.stderr)

def diff_list(l1, l2):
    assert len(l1) <= len(l2)
    if l1 == l2:
        return []
    else:
        return l2[len(l1):]

class Monitor:
    def __init__(self, monitor_file, process):
        self.monitor_file = monitor_file
        self.process = process
        self.updated_time = datetime.now()
        self.start_time = self.updated_time
        self.last_content = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.process.kill()
    
    def poll(self):
        return self.process.poll()
    
    def check(self):
        last_updated_time = self.updated_time
        current_time = datetime.now()
        with open(self.monitor_file, 'r') as f:
            content = list(map(lambda l: l.strip(), f.readlines()))
            diff = diff_list(self.last_content, content)
            if diff:
                self.last_content = content
                self.updated_time = current_time
                return True, current_time, current_time - current_time, diff
        return False, last_updated_time, current_time - last_updated_time, content

def execute(cmd, monitor_file):
    with open(monitor_file, 'w') as f:
        popen = subprocess.Popen(cmd, stdout=sys.stdout, stderr=f, universal_newlines=True)
    return Monitor(monitor_file, popen)

TIME_LIMIT = 180
PRINT_PROGRESS = False

def try_run_phasar():
    cmd = ['bash', '/tmp/run_phasar.sh']
    with execute(cmd, '/src/monitor-stderr.log') as monitor:
        current_period = 0
        while current_period < 2 and monitor.poll() is None:
            time.sleep(10)
            now = datetime.now()
            logger.info(f'Check at {now - monitor.start_time}')
            updated, _, elapsed, content = monitor.check()
            if current_period == 0:
                if updated:
                    if PRINT_PROGRESS:
                        for l in content:
                            print(l)
                    if 'Analyzing function' in content[-1]:
                        current_period = 1
                if not PRINT_PROGRESS:
                    logger.info(f'{"Updated" if updated else "Not updated"}, elapsed: {elapsed}')
            elif current_period == 1:
                if 'Analyzing function' in content[-1]:
                    if not updated and elapsed.total_seconds() > TIME_LIMIT:
                        stripped = content[-1].split('-')[-1].strip()
                        assert stripped.startswith('[DEBUG] Analyzing function: ')
                        func = stripped[len('[DEBUG] Analyzing function: '):]
                        logger.info(f'Func get stuck: {func}')
                        return func
                    else:
                        if updated:
                            if PRINT_PROGRESS:
                                for l in content:
                                    print(l)
                    if not PRINT_PROGRESS:
                        logger.info(f'{"Updated" if updated else "Not updated"}, elapsed: {elapsed}')
                else:
                    if updated:
                        if PRINT_PROGRESS:
                            for l in content:
                                print(l)
                    if not PRINT_PROGRESS:
                        logger.info(f'{"Updated" if updated else "Not updated"}, elapsed: {elapsed}')
                    current_period = 2
                    
    return None

FILE = '/phasar/lib/PhasarLLVM/Pointer/LLVMPointsToSet.cpp'
LINE_NO = 359
    
def modify_phasar(conds):
    with open(FILE, 'r') as f:
        lines = f.readlines()
        line = lines[LINE_NO].strip()
        logger.info(f'Previous line: {line}')
        assert line.startswith('return')
    lines[LINE_NO] = f'return ' + ' || '.join(conds) + ';\n'
    with open(FILE, 'w') as f:
        f.writelines(lines)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    with open(FILE, 'r') as f:
        lines = f.readlines()
        line = lines[LINE_NO].strip()
        assert line.startswith('return')
        while line.endswith(';'):
            line = line[:-1]
        stripped = line[len('return '):]
        conds = stripped.split(' || ')
    modify_phasar(conds) 
    
    round = len(conds) - 1
    while True:
        logger.info(f'Round {round} begin')
        rebuild_phasar()
        func = try_run_phasar()
        round += 1
        if func is None:
            break
        new_cond = f'F->getName() == "{func}"'
        conds.append(new_cond)
        with open('/src/funcs_fallback_to_steens.txt', 'a') as f:
            f.write(f'{new_cond}\n')
        modify_phasar(conds)
    
    logger.info(f'Func skipped: {", ".join(conds)}')
    with open('/src/funcs_fallback_to_steens.txt', 'w') as f:
        for cond in conds:
            f.write(f'{cond}\n')
