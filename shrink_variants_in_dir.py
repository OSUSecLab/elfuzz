import os
import click
import subprocess
import sys
from typing import List

@click.command()
@click.option('--source-dir', 'source_dir', type=click.Path(exists=True))
def main(source_dir: click.Path):
    # print(f'Shrink files in {str(source_dir)}...', file=sys.stderr)
    ps: List[subprocess.Popen] = []
    for p, ds, fs in os.walk(str(source_dir)):
        for f in fs:
            if f.endswith('.py'):
                file = os.path.join(p, f)
                ps.append(subprocess.Popen(['python', 'shrink_variant.py', file]))
    for p in ps:
        p.wait()

if __name__ == '__main__':
    main()
