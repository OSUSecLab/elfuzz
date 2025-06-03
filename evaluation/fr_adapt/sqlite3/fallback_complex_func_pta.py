import os
import sys
import subprocess

import logging

START_SECONDS = 40
STEP = 0.5

logger = logging.getLogger(__file__)

def rebuild_phasar():
    build_cmd = ['cmake', '--build', '/phasar/build']
    install_cmd = ['cmake', '-DCMAKE_INSTALL_PREFIX', '/usr/local/phasar', '-P', '/phasar/build/cmake_install.cmake']

    subprocess.run(build_cmd, stdout=sys.stdout, stderr=sys.stderr)
    subprocess.run(install_cmd, stdout=sys.stdout, stderr=sys.stderr)

def try_run_phasar(timeout):
    cmd = ['bash', '/tmp/fr/programs/sqlite3_elm/run_phasar.sh']
    try:
        subprocess.run(cmd, capture_output=True, timeout=timeout, text=True)
    except subprocess.TimeoutExpired as err:
        stderr = err.stderr.decode('utf-8')
        lines = stderr.split('\n')
        last_line = lines[-1]

        logger.info(f'Last line: {last_line}')

        if '-' not in last_line:
            print('STDERR:'+'\n'.join(lines))
            return None
        
        _, trimmed = last_line.split('-')
        trimmed = trimmed.strip()
        if trimmed.startswith('[DEBUG] Analyzing function: '):
            func = trimmed[len('[DEBUG] Analyzing function: '):]
            logger.debug(f'Func get stuck: {func}')
            return func
    print('STDERR:'+'\n'.join(lines))
    return None

FILE = '/phasar/lib/PhasarLLVM/Pointer/LLVMPointsToSet.cpp'
LINE_NO = 114
    
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
        logger.info(f'Original line: {line}')
        assert line.startswith('return')
        while line.endswith(';'):
            line = line[:-1]
        stripped = line[len('return '):]
        conds = stripped.split(' || ')
    modify_phasar(conds) 
    
    round = len(conds) - 1
    while True:
        logger.info(f'Round {round}')
        rebuild_phasar()
        logger.info(f'Attempt run {START_SECONDS + STEP * round} seconds')
        func = try_run_phasar(START_SECONDS + STEP * round)
        round += 1
        if func is None:
            break
        conds.append(f'F->getName() == "{func}"')
        modify_phasar(conds)
    
    logger.info(f'Func skipped: {", ".join(conds)}')
    with open('/src/skip_funcs.txt', 'w') as f:
        for cond in conds:
            f.write(f'{cond}\n')
