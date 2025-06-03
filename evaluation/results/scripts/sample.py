import random
import click as clk
import os
import os.path


@clk.command()
@clk.option('--input', '-i', type=clk.Path(exists=True))
@clk.option('--output', '-o', type=clk.Path(exists=False), default='-')
@clk.option('--sample-size', '-s', type=int, default=3000)
def main(input, output, sample_size):
    files = os.listdir(input)
    sample = random.sample(files, sample_size)
    with clk.open_file(output, 'w') as f:
        f.writelines('\n'.join(sample))

if __name__ == '__main__':
    main()
