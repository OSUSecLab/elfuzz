import click as clk
import os.path
import subprocess
import sys

FUNCTIONS = {
    'libxml2': 'generate_xml',
    'jsoncpp': 'generate_json',
    're2': 'generate_regex',
    'librsvg': 'generate_svg',
    'cpython3': 'generate_python3',
    'sqlite3': 'generate_sql',
    'cvc5': 'generate_smtlib2'
}

@clk.command()
@clk.option('--fuzzer', '-z', type=clk.Choice(['elm', 'alt']))
@clk.argument('benchmark', type=clk.Choice(list(FUNCTIONS.keys())))
@clk.option('--time', '-t', type=int, default=600, required=False)
@clk.option('--para', '-j', type=int, default=5, required=False)
def main(benchmark, fuzzer, time, para):
    CWD = os.path.dirname(__file__)
    workdir = os.path.join(CWD, 'workdir', f'{benchmark}_{fuzzer}')
    gendir = os.path.join(CWD, 'workdir', f'{benchmark}_{fuzzer}_gen')

    cmd = [
        'python',
        os.path.join(workdir, 'driver.py'),
        '-o', gendir,
        '-t', str(time),
        '-j', str(para),
        '-g', FUNCTIONS[benchmark]
    ]
    subprocess.run(cmd, check=True, stdout=sys.stdout, stderr=sys.stderr)

if __name__ == '__main__':
    main()
