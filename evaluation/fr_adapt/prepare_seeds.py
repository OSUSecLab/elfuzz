import click
import os.path
import os
import subprocess
from tqdm import tqdm
import tempfile
import shutil

@click.command()
@click.option('--input-dir', '-i', required=True, help='Input directory', type=click.Path(exists=True, dir_okay=True, file_okay=False))
@click.option('--output-dir', '-o', required=True, help='Output directory', type=click.Path(exists=False, dir_okay=True, file_okay=False))
def main(input_dir, output_dir):
    for p, ds, fs in tqdm(os.walk(input_dir)):
        for f in fs:
            archive_filename = os.path.join(p, f)
            with tempfile.TemporaryDirectory() as tmp_dir:
                cmd = ['tar', '--zstd', '-xf', archive_filename, '-C', tmp_dir]
                subprocess.run(cmd, check=True)
                tmp = os.listdir(tmp_dir)
                assert len(tmp) == 1
                prefix = tmp[0]
                seeds = os.listdir(os.path.join(tmp_dir, prefix))
                for seed in seeds:
                    shutil.copy(os.path.join(tmp_dir, prefix, seed), os.path.join(output_dir, f'{prefix}_{seed}'))
if __name__ == '__main__':
    main()
