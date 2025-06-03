import os
import os.path as path
import click
import re
import itertools
import pandas as pd

FUZZERS = [
    'elm',
    'alt',
    'grmr',
    'isla',
    'islearn'
]

BENCHMARKS = [
    'libxml2',
    're2',
    'cpython3',
    'sqlite3',
    'cvc5',
    'librsvg'
]

EXCLUDES = [('re2', 'islearn')]

@click.command()
@click.option('--input', '-i', required=True, help='Input directory', 
              type=click.Path(exists=True, dir_okay=True, file_okay=False))
@click.option('--output', '-o', required=False, help='Output directory',
              type=click.Path(dir_okay=False, file_okay=True, exists=False), default='-')
@click.option('--transpose', '-t', is_flag=True, help='Transpose the output', default=True)
@click.option('--fix-mode', is_flag=True, help='Fix mode', default=False)
def main(input, output, transpose, fix_mode):
    outfile = output
    dfs = {}
    
    if fix_mode:
        for (benchmark, fuzzer) in itertools.product(BENCHMARKS, FUZZERS):
            if (benchmark, fuzzer) in EXCLUDES:
                continue
            count_file = path.join(
                input, f'{benchmark}_{fuzzer}', 'count'
            )
            cov_file = path.join(
                input, f'{benchmark}_{fuzzer}', 'cov'
            )
            with open(cov_file, 'r') as cov_f:
                count = len(list(filter(lambda l: l.strip(), cov_f.readlines())))
            with open(count_file, 'w') as count_f:
                count_f.write(str(count))
        return
    
    for fuzzer in FUZZERS:
        df = pd.read_excel(
            path.join(outfile),
            sheet_name=fuzzer,
            header=0,
            index_col=0
        )
        dfs[fuzzer] = df
    
    with pd.ExcelWriter(outfile) as writer:
        for fuzzer in FUZZERS:
            df = dfs[fuzzer]
            for benchmark in BENCHMARKS:
                if (benchmark, fuzzer) in EXCLUDES:
                    continue
                count_file = path.join(
                    input, f'{benchmark}_{fuzzer}', 'count'
                )
                with open(count_file, 'r') as count_f:
                    count = int(count_f.read())
                df.loc[0, benchmark] = count
            df.to_excel(writer, sheet_name=fuzzer)

if __name__ == '__main__':
    main()