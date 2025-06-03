import click as clk
import os
import os.path
import tempfile
import subprocess
import shutil
import logging

logger = logging.getLogger(__file__)

@clk.command()
@clk.option('--fuzzer', '-z', type=clk.Choice([
    'elm', 'alt', 'grmr'
]))
@clk.argument('benchmark', type=clk.Choice([
    'libxml2', 'jsoncpp', 'cpython3', 'cvc5', 'librsvg', 'sqlite3', 're2'
]))
@clk.option('--force', '-f', is_flag=True)
def main(fuzzer: str, benchmark: str, force):
    cwd = os.path.dirname(os.path.abspath(__file__))
    
    workdir = os.path.join(cwd, 'workdir', f'{benchmark}_{fuzzer}')
    
    if os.path.exists(workdir):
        if not force:
            logger.error(f'Workdir {workdir} already exists. Use --force to overwrite.')
            return
        shutil.rmtree(workdir)
    if os.path.exists(os.path.join(cwd, 'workdir', f'{benchmark}_{fuzzer}_gen')):
        shutil.rmtree(os.path.join(cwd, 'workdir', f'{benchmark}_{fuzzer}_gen'))
    os.makedirs(workdir)
    os.makedirs(os.path.join(cwd, 'workdir', f'{benchmark}_{fuzzer}_gen'))
    
    match fuzzer:
        case 'elm' | 'alt':
            shutil.copy2(os.path.join(cwd, 'elmdriver.py'), os.path.join(workdir, 'driver.py'))
            fuzzer_dir = os.path.join(cwd, '..', 'elmfuzzers' if fuzzer == 'elm' else 'alt_elmfuzzers')
            fuzzer_files = os.listdir(fuzzer_dir)
            for f in fuzzer_files:
                if f.startswith(benchmark):
                    fuzzer_file = os.path.join(fuzzer_dir, f)
                    break
            with tempfile.TemporaryDirectory() as tempdir:
                cmd = [
                    'tar', 'xJf', fuzzer_file, '-C', tempdir
                ]
                subprocess.run(cmd, check=True)
                unzipped_dir = os.path.join(tempdir, os.path.split(fuzzer_file)[1].removesuffix('.tar.xz'))
                py_files = list(filter(lambda f: f.endswith('.py'), os.listdir(unzipped_dir)))
                
                for f in py_files:
                    shutil.copy2(os.path.join(unzipped_dir, f), 
                                 os.path.join(workdir, 
                                              f.removesuffix('.py')
                                               .replace('.', '_')
                                               .replace('-', '_') + '.py'))
        case 'grmr':
            previous_workdir = os.path.join(cwd, '..', 'workdir', f'{benchmark}_grammarinator')
            for f in os.listdir(previous_workdir):
                if not os.path.isfile(os.path.join(previous_workdir, f)):
                    continue
                shutil.copy2(os.path.join(previous_workdir, f), os.path.join(workdir, f))
            shutil.copy2(os.path.join(cwd, 'grmrdriver.py'), os.path.join(workdir, 'driver.py'))
    
if __name__ == '__main__':
    main()
