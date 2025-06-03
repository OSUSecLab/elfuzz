import os
import click
import subprocess
import shutil
import sys

zest_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'zest'))

@click.command()
@click.argument('project', type=click.Choice(['cvc5']))
def prepare_zest(project):
    cmd = ['python', 'prepare.py', '-z', 'elm', project]
    subprocess.run(cmd, check=True, stdout=sys.stdout, stderr=sys.stderr)

    shutil.move(project, f'{project}_zest')

    patch = os.path.join(zest_dir, f'{project}_driver_modify.diff')

    cmd = ['patch', '-d', f'{project}_zest', '-i', patch, 'driver.py']
    subprocess.run(cmd, check=True, stderr=sys.stderr, stdout=sys.stdout)

    click.echo(f'{project}_zest is ready for Zest')

if __name__ == '__main__':
    prepare_zest()
