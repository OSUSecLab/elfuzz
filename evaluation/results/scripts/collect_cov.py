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

USE_PATCHED = [
    're2', 'cpython3', 'sqlite3'
]

EXCLUDES = [('re2', 'islearn')]

SPLIT_POINTS = [
    600, 1200, 1800, 2400, 3000, 3600
]

@click.command()
@click.option('--input', '-i', required=True, help='Input directory', 
              type=click.Path(exists=True, dir_okay=True, file_okay=False))
@click.option('--output', '-o', required=True, help='Output directory',
              type=click.Path(dir_okay=True, file_okay=False, exists=True))
@click.option('--transpose', '-t', is_flag=True, help='Transpose the output', default=False)
def main(input, output, transpose):
    orig = path.join(input, 'orig')
    orig_dirs = os.listdir(orig)
    orig_repetitions = list(map(
        lambda dir_name: int(dir_name[3:]),
        filter(
            lambda dir_name: re.match(r'out\d+', dir_name),
            orig_dirs
        )
    ))
    
    patched = path.join(input, 'patched')
    patched_dirs = os.listdir(patched)
    patched_repetitions = list(map(
        lambda dir_name: int(dir_name[3:]),
        filter(
            lambda dir_name: re.match(r'out\d+', dir_name),
            patched_dirs
        )
    ))
    
    assert orig_repetitions == patched_repetitions
    
    for it in orig_repetitions:
        outfile = path.join(output, f'rep{it}.xlsx')
        if path.exists(outfile):
            os.remove(outfile)
        with pd.ExcelWriter(outfile) as writer:
            if not transpose:
                for benchmark in BENCHMARKS:
                    data = {}
                    for fuzzer in FUZZERS:
                        if (benchmark, fuzzer) in EXCLUDES:
                            data[fuzzer] = [None] * (len(SPLIT_POINTS) + 1)
                            continue
                        orig_plot_file = path.join(
                            orig, f'out{it}', f'{benchmark}_{fuzzer}', 'default', 'plot_data'
                        )
                        patched_plot_file = path.join(
                            patched, f'out{it}', f'{benchmark}_{fuzzer}', 'default', 'plot_data'
                        )
                        if fuzzer in USE_PATCHED:
                            plot_file = patched_plot_file
                        else:
                            plot_file = orig_plot_file
                        
                        records = [None]
                        with open(plot_file) as f:
                            first_line = True
                            last_sec = 0
                            next_split = 0
                            for l in f:
                                if next_split == len(SPLIT_POINTS):
                                    break
                                if first_line:
                                    first_line = False
                                    continue
                                tokens = l.split(',')
                                sec = int(tokens[0].strip())
                                edges = int(tokens[-1].strip())
                                if last_sec < SPLIT_POINTS[next_split] and sec >= SPLIT_POINTS[next_split]:
                                    records.append(edges)
                                    next_split += 1
                                    last_sec = sec
                        data[fuzzer] = records
                    data_frame = pd.DataFrame(
                        data,
                        index=[0] + SPLIT_POINTS
                    )
                    data_frame.index.name = 'time'
                    data_frame.to_excel(writer, sheet_name=benchmark)
            else:
                for fuzzer in FUZZERS:
                    data = {}
                    for benchmark in BENCHMARKS:
                        if (benchmark, fuzzer) in EXCLUDES:
                            data[benchmark] = [None] * (len(SPLIT_POINTS) + 1)
                            continue
                        orig_plot_file = path.join(
                            orig, f'out{it}', f'{benchmark}_{fuzzer}', 'default', 'plot_data'
                        )
                        patched_plot_file = path.join(
                            patched, f'out{it}', f'{benchmark}_{fuzzer}', 'default', 'plot_data'
                        )
                        if fuzzer in USE_PATCHED:
                            plot_file = patched_plot_file
                        else:
                            plot_file = orig_plot_file
                        
                        records = [None]
                        with open(plot_file) as f:
                            first_line = True
                            last_sec = 0
                            next_split = 0
                            for l in f:
                                if next_split == len(SPLIT_POINTS):
                                    break
                                if first_line:
                                    first_line = False
                                    continue
                                tokens = l.split(',')
                                sec = int(tokens[0].strip())
                                edges = int(tokens[-1].strip())
                                if last_sec < SPLIT_POINTS[next_split] and sec >= SPLIT_POINTS[next_split]:
                                    records.append(edges)
                                    next_split += 1
                                    last_sec = sec
                        data[benchmark] = records
                    data_frame = pd.DataFrame(
                        data,
                        index=[0] + SPLIT_POINTS
                    )
                    data_frame.index.name = 'time'
                    data_frame.to_excel(writer, sheet_name=fuzzer)

if __name__ == '__main__':
    main()